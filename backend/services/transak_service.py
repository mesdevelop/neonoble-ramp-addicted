"""
Transak integration service (staging).

This service is intentionally THIN: NeoNoble does not custody funds,
does not route trades, and does not hold private keys. Its only role is:

  1. Expose a public, read-only config to the frontend (api key + env).
  2. Decide whether the user's preferred token (NENO) is available on
     Transak staging or whether the UI should fall back to USDC on BSC.
  3. Log Transak widget events the frontend forwards back to us, for
     compliance/audit and customer support — never as a trade trigger.

Compliance pillars enforced at this layer:
  - User-initiated Only:  no backend endpoint *creates* a trade.
                          We only persist events emitted by the user's
                          own Transak widget session.
  - No Fund Intermediation: no payout, payment, custody or routing API.
  - Direct Delivery:        we never read or write the user's wallet
                          address from our DB into the widget params.
                          The frontend passes the user's connected
                          wallet directly to Transak.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# NENO BEP-20 contract (mainnet). Same value used by the blockchain listener.
NENO_CONTRACT_ADDRESS = "0xeF3F5C1892A8d7A3304E4A15959E124402d69974"

# Transak does NOT list NENO in its supported assets on staging today.
# Until Transak adds the NENO listing, the widget will fall back to USDC
# on BSC. This flag is environment-tunable so we can flip it the moment
# Transak whitelists the contract above.
SUPPORTS_NENO_DEFAULT = False


class TransakService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.events_collection = db.transak_events

    async def initialize(self):
        await self.events_collection.create_index("wallet_address")
        await self.events_collection.create_index("event_type")
        await self.events_collection.create_index("order_id")
        await self.events_collection.create_index("created_at")

    def get_public_config(self) -> dict:
        """Public, read-only Transak config for the frontend."""
        supports_neno = (
            os.environ.get("TRANSAK_SUPPORTS_NENO", "")
            .strip()
            .lower()
            in ("1", "true", "yes")
        ) or SUPPORTS_NENO_DEFAULT

        return {
            "api_key": os.environ.get("TRANSAK_API_KEY", ""),
            "environment": os.environ.get("TRANSAK_ENVIRONMENT", "STAGING"),
            "referrer_domain": os.environ.get("TRANSAK_REFERRER_DOMAIN", ""),
            "network": "bsc",
            "fiat_currency": os.environ.get("TRANSAK_DEFAULT_FIAT", "EUR"),
            "neno_contract": NENO_CONTRACT_ADDRESS,
            "supports_neno": supports_neno,
            # Token the UI should use until Transak lists NENO on staging
            "fallback_token": os.environ.get("TRANSAK_FALLBACK_TOKEN", "USDC"),
            # Compliance attestation surfaced in the UI for the walkthrough
            "non_custodial": True,
            "compliance": {
                "user_initiated_only": True,
                "no_fund_intermediation": True,
                "direct_delivery": True,
            },
        }

    async def record_event(
        self,
        wallet_address: str,
        event_type: str,
        payload: dict,
        user_id: Optional[str] = None,
    ) -> str:
        """Persist a Transak widget event forwarded by the frontend."""
        order_id = None
        if isinstance(payload, dict):
            # Common Transak event payload shapes
            data = payload.get("status") or payload.get("data") or {}
            if isinstance(data, dict):
                order_id = data.get("id") or data.get("orderId")

        doc = {
            "user_id": user_id,
            "wallet_address": (wallet_address or "").lower(),
            "event_type": event_type,
            "order_id": order_id,
            "payload": payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await self.events_collection.insert_one(doc)
        logger.info(
            f"Transak event recorded: {event_type} for wallet "
            f"{wallet_address[:10] if wallet_address else 'n/a'}... "
            f"(order: {order_id or 'n/a'})"
        )
        return str(result.inserted_id)

    async def list_events_for_wallet(self, wallet_address: str, limit: int = 50) -> list:
        cursor = (
            self.events_collection
            .find({"wallet_address": wallet_address.lower()}, {"_id": 0})
            .sort("created_at", -1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)
