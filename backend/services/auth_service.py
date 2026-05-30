from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List
from datetime import datetime, timezone
import logging

from models.user import User, UserCreate, UserResponse, UserRole
from utils.password import hash_password, verify_password
from utils.jwt_utils import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.users
    
    async def register(self, user_data: UserCreate) -> tuple[Optional[User], Optional[str]]:
        """Register a new user.
        
        Returns:
            Tuple of (User, None) on success, or (None, error_message) on failure
        """
        try:
            # Check if email already exists
            existing = await self.collection.find_one({"email": user_data.email})
            if existing:
                logger.warning(f"Registration failed: email already exists - {user_data.email}")
                return None, "Email already registered"
            
            # Create user
            password_hash = hash_password(user_data.password)
            user = User(
                email=user_data.email,
                password_hash=password_hash,
                role=user_data.role
            )
            
            # Save to database
            user_dict = user.model_dump()
            user_dict['created_at'] = user_dict['created_at'].isoformat()
            user_dict['updated_at'] = user_dict['updated_at'].isoformat()
            
            await self.collection.insert_one(user_dict)
            logger.info(f"User registered successfully: {user.email} (role: {user.role})")
            
            return user, None
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return None, f"Registration failed: {str(e)}"
    
    async def login(self, email: str, password: str) -> tuple[Optional[dict], Optional[str]]:
        """Login a user.
        
        Returns:
            Tuple of ({access_token, refresh_token, user_id, email, role}, None) on success,
            or (None, error_message) on failure
        """
        try:
            # Find user
            user_doc = await self.collection.find_one({"email": email})
            if not user_doc:
                logger.warning(f"Login failed: user not found - {email}")
                return None, "Invalid email or password"
            
            # Verify password
            if not verify_password(password, user_doc['password_hash']):
                logger.warning(f"Login failed: incorrect password - {email}")
                return None, "Invalid email or password"
            
            # Check if active
            if not user_doc.get('is_active', True):
                logger.warning(f"Login failed: user inactive - {email}")
                return None, "Account is deactivated"
            
            tokens = self._issue_tokens(user_doc)
            logger.info(f"User logged in: {email}")
            return tokens, None
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return None, f"Login failed: {str(e)}"

    def _issue_tokens(self, user_doc: dict) -> dict:
        """Issue a fresh access + refresh token pair for a user document."""
        access_token = create_access_token(
            user_id=user_doc['id'],
            email=user_doc['email'],
            role=user_doc['role'],
        )
        refresh_token = create_refresh_token(
            user_id=user_doc['id'],
            email=user_doc['email'],
            role=user_doc['role'],
        )
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user_id': user_doc['id'],
            'email': user_doc['email'],
            'role': user_doc['role'],
        }

    async def refresh_tokens(self, user_id: str) -> Optional[dict]:
        """Issue a new token pair for the given user_id (used by /auth/refresh)."""
        user_doc = await self.collection.find_one({"id": user_id})
        if not user_doc or not user_doc.get('is_active', True):
            return None
        return self._issue_tokens(user_doc)
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        user_doc = await self.collection.find_one({"id": user_id})
        if user_doc:
            # Convert ISO strings back to datetime
            if isinstance(user_doc.get('created_at'), str):
                user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
            if isinstance(user_doc.get('updated_at'), str):
                user_doc['updated_at'] = datetime.fromisoformat(user_doc['updated_at'])
            return User(**user_doc)
        return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        user_doc = await self.collection.find_one({"email": email})
        if user_doc:
            if isinstance(user_doc.get('created_at'), str):
                user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
            if isinstance(user_doc.get('updated_at'), str):
                user_doc['updated_at'] = datetime.fromisoformat(user_doc['updated_at'])
            return User(**user_doc)
        return None
    
    def user_to_response(self, user: User) -> UserResponse:
        """Convert User to UserResponse (without sensitive data)."""
        return UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )
