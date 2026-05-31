from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from models.user import UserCreate, UserResponse, UserRole
from services.auth_service import AuthService
from middleware.auth import get_current_user
from utils.jwt_utils import decode_refresh_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Service will be set by the main app
auth_service: AuthService = None


def set_auth_service(service: AuthService):
    global auth_service
    auth_service = service


class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str = "USER"  # USER or DEVELOPER


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    # New short-lived access token + long-lived refresh token
    token: Optional[str] = None  # alias for access_token, kept for backwards compatibility
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[UserResponse] = None


def _build_auth_response(tokens: dict, user, message: str) -> AuthResponse:
    return AuthResponse(
        success=True,
        message=message,
        token=tokens['access_token'],
        access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        user=auth_service.user_to_response(user),
    )


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """Register a new user."""
    try:
        try:
            role = UserRole(request.role.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}",
            )

        user_create = UserCreate(email=request.email, password=request.password, role=role)
        user, error = await auth_service.register(user_create)
        if error:
            logger.warning(f"Registration failed for {request.email}: {error}")
            raise HTTPException(status_code=400, detail=error)

        # Auto-login after registration (uses the persisted, normalized email)
        tokens, login_error = await auth_service.login(user.email, request.password)
        if not tokens:
            logger.error(
                f"Auto-login after registration failed for {user.email}: {login_error}"
            )
            raise HTTPException(
                status_code=500,
                detail="Registration succeeded but auto-login failed. Please log in manually.",
            )
        return _build_auth_response(tokens, user, "Registration successful")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login with email and password."""
    try:
        tokens, error = await auth_service.login(request.email, request.password)
        if error:
            logger.warning(f"Login failed for {request.email}: {error}")
            raise HTTPException(status_code=401, detail=error)

        user = await auth_service.get_user_by_email(request.email)
        return _build_auth_response(tokens, user, "Login successful")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/refresh", response_model=AuthResponse)
async def refresh(request: RefreshRequest):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    payload = decode_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    tokens = await auth_service.refresh_tokens(payload['sub'])
    if not tokens:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    user = await auth_service.get_user_by_id(payload['sub'])
    return _build_auth_response(tokens, user, "Token refreshed")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    user = await auth_service.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return auth_service.user_to_response(user)


@router.post("/logout")
async def logout():
    """Logout (client should discard tokens)."""
    return {"success": True, "message": "Logged out successfully"}
