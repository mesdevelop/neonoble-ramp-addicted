"""
Backend tests for the Transak STAGING widget integration.

Covers:
- GET /api/transak/config (public, env-driven)
- POST /api/transak/events (auth-optional, anonymous + authed)
- GET  /api/transak/events?wallet_address=... (read back)
- Negative cases (empty wallet_address, missing query param)
- Compliance attestation: /api/transak namespace exposes NO trade/payout endpoint
"""
import uuid
import requests


# ---------- /api/transak/config ----------

class TestTransakConfig:
    def test_config_returns_public_widget_config(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/transak/config")
        assert r.status_code == 200, r.text
        d = r.json()
        # Required fields
        assert d.get("api_key"), "api_key must be set"
        # Public staging key from Transak docs
        assert d["api_key"] == "8be07021-eb1d-431a-8e9f-67bd2cf7bce9"
        assert d["environment"] == "STAGING"
        assert d["supports_neno"] is False
        assert d["fallback_token"] == "USDC"
        assert d["neno_contract"] == "0xeF3F5C1892A8d7A3304E4A15959E124402d69974"
        assert d["network"] == "bsc"
        assert d["fiat_currency"] == "EUR"
        assert d["non_custodial"] is True
        # Compliance attestation
        c = d.get("compliance") or {}
        assert c.get("user_initiated_only") is True
        assert c.get("no_fund_intermediation") is True
        assert c.get("direct_delivery") is True


# ---------- /api/transak/events ----------

class TestTransakEvents:
    def test_post_event_anonymous_succeeds(self, api_client, base_url):
        wallet = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"  # 40+ hex chars
        r = api_client.post(
            f"{base_url}/api/transak/events",
            json={
                "wallet_address": wallet,
                "event_type": "TRANSAK_WIDGET_INITIALISED",
                "payload": {"source": "test_anonymous"},
            },
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["success"] is True
        assert isinstance(d["event_id"], str) and len(d["event_id"]) > 0

    def test_post_event_with_auth_succeeds(self, base_url, user_authed_client):
        wallet = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"
        r = user_authed_client.post(
            f"{base_url}/api/transak/events",
            json={
                "wallet_address": wallet,
                "event_type": "TRANSAK_ORDER_CREATED",
                "payload": {"data": {"id": "order-xyz"}},
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["success"] is True

    def test_post_event_empty_wallet_returns_400_or_422(self, api_client, base_url):
        # Empty wallet_address: route handler raises 400, but Pydantic may
        # accept an empty string. Either way it must not succeed (>=400).
        r = api_client.post(
            f"{base_url}/api/transak/events",
            json={
                "wallet_address": "",
                "event_type": "TRANSAK_WIDGET_INITIALISED",
                "payload": {},
            },
        )
        # 400 (handler) or 422 (pydantic) acceptable; 200 is a bug.
        assert r.status_code in (400, 422), f"expected client error, got {r.status_code}: {r.text}"

    def test_get_events_returns_logged_events_lowercased(self, api_client, base_url):
        # Use mixed-case so we can verify the backend lowercases the storage key
        wallet_mixed = f"0xAbCdEf{uuid.uuid4().hex[:34]}"
        wallet_lower = wallet_mixed.lower()
        # Log two events
        for et in ("TRANSAK_WIDGET_OPEN", "TRANSAK_ORDER_SUCCESSFUL"):
            r = api_client.post(
                f"{base_url}/api/transak/events",
                json={
                    "wallet_address": wallet_mixed,
                    "event_type": et,
                    "payload": {"data": {"orderId": f"o_{uuid.uuid4().hex[:6]}"}},
                },
            )
            assert r.status_code == 200, r.text

        # Query by lowercase variant - service lowercases server-side
        r = api_client.get(
            f"{base_url}/api/transak/events",
            params={"wallet_address": wallet_lower},
        )
        assert r.status_code == 200, r.text
        events = r.json()
        assert isinstance(events, list)
        assert len(events) >= 2
        # Each event's stored wallet_address must be lowercased
        for e in events:
            assert e["wallet_address"] == wallet_lower
        # Event types must include both we logged
        types = {e["event_type"] for e in events}
        assert "TRANSAK_WIDGET_OPEN" in types
        assert "TRANSAK_ORDER_SUCCESSFUL" in types
        # MongoDB _id must NOT leak (server uses {_id: 0} projection)
        for e in events:
            assert "_id" not in e

    def test_get_events_missing_wallet_returns_422(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/transak/events")
        # Pydantic/FastAPI validation for required query param
        assert r.status_code == 422


# ---------- Compliance: /api/transak namespace has NO trade endpoint ----------

class TestTransakCompliance:
    def test_no_trade_or_payout_endpoint_under_transak_namespace(self, api_client, base_url):
        """
        Compliance attestation: the only mutating endpoint under /api/transak
        is the observational /events log. There must be NO trade/payout/order
        creation endpoint. We probe a few likely names and assert they 404.
        """
        forbidden_paths = [
            "/api/transak/trade",
            "/api/transak/trades",
            "/api/transak/order",
            "/api/transak/orders",
            "/api/transak/payout",
            "/api/transak/payouts",
            "/api/transak/buy",
            "/api/transak/sell",
            "/api/transak/swap",
            "/api/transak/transfer",
        ]
        for path in forbidden_paths:
            r = api_client.post(f"{base_url}{path}", json={})
            assert r.status_code == 404, (
                f"{path} unexpectedly exists "
                f"(status={r.status_code}). /api/transak must NOT expose "
                "any trade/payout endpoint."
            )

    def test_openapi_does_not_define_trade_routes(self, api_client, base_url):
        """Inspect the OpenAPI schema - only /config + /events should exist
        under /api/transak."""
        r = requests.get(f"{base_url}/api/openapi.json", timeout=20)
        # FastAPI default is /openapi.json (not /api/openapi.json); try both
        if r.status_code != 200:
            r = requests.get(f"{base_url}/openapi.json", timeout=20)
        import pytest
        if r.status_code != 200:
            pytest.skip("openapi schema not exposed publicly; covered by 404 probes")
        try:
            spec = r.json()
        except ValueError:
            pytest.skip("openapi endpoint not returning JSON via ingress; covered by 404 probes")
        transak_paths = [p for p in spec.get("paths", {}).keys() if "/transak" in p]
        # Allowed: /api/transak/config, /api/transak/events
        allowed_suffixes = {"/transak/config", "/transak/events"}
        for p in transak_paths:
            assert any(p.endswith(s) for s in allowed_suffixes), (
                f"Unexpected Transak route in OpenAPI: {p}"
            )
