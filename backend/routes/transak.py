"""
Transak integration routes (staging).

All endpoints are intentionally observational:
  GET  /api/transak/config         -> public widget config (api key + env)
  POST /api/transak/events         -> log a widget event from the user's
                                       own session (NOT a trade trigger)
  GET  /api/transak/events         -> read back the caller's events for
                                       the connected wallet

There is NO endpoint that creates, routes, or settles a trade — the
Transak widget runs in the user's browser and settles directly to the
user's wallet. This is what "non-custodial + no fund intermediation"
means at the API layer.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
import logging

from middleware.auth import get_optional_user
from services.transak_service import TransakService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transak", tags=["Transak"])

# Service is wired by main app
transak_service: Optional[TransakService] = None


def set_transak_service(service: TransakService):
    global transak_service
    transak_service = service


class TransakEventRequest(BaseModel):
    wallet_address: str = Field(..., description="User's connected wallet address")
    event_type: str = Field(..., description="Transak event name, e.g., TRANSAK_ORDER_SUCCESSFUL")
    payload: Dict[str, Any] = Field(default_factory=dict)


class TransakEventResponse(BaseModel):
    success: bool
    event_id: str


@router.get("/config")
async def get_config():
    """Return the public, read-only Transak widget config."""
    if not transak_service:
        raise HTTPException(status_code=503, detail="Transak service not ready")
    config = transak_service.get_public_config()
    if not config.get("api_key"):
        raise HTTPException(
            status_code=503,
            detail="TRANSAK_API_KEY not configured on backend",
        )
    return config


@router.post("/events", response_model=TransakEventResponse)
async def log_event(
    request: TransakEventRequest,
    current_user: Optional[dict] = Depends(get_optional_user),
):
    """Log a Transak widget event forwarded by the frontend."""
    if not transak_service:
        raise HTTPException(status_code=503, detail="Transak service not ready")
    if not request.wallet_address:
        raise HTTPException(status_code=400, detail="wallet_address is required")

    event_id = await transak_service.record_event(
        wallet_address=request.wallet_address,
        event_type=request.event_type,
        payload=request.payload,
        user_id=current_user.get("user_id") if current_user else None,
    )
    return TransakEventResponse(success=True, event_id=event_id)


@router.get("/events")
async def list_events(
    wallet_address: str = Query(..., min_length=10, max_length=64),
    limit: int = Query(50, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """Read back a wallet's recent Transak events for the demo / audit."""
    if not transak_service:
        raise HTTPException(status_code=503, detail="Transak service not ready")
    return await transak_service.list_events_for_wallet(wallet_address, limit=limit)
