"""Tests for the iteration_3 work:
- Case-insensitive email register + login (P0 regression)
- /api/auth/forgot-password (no enumeration + console-fallback email log)
- /api/auth/reset-password (single-use token, validation)
- /api/auth/change-password (auth + current_password check)
- Welcome email triggered on register (console fallback)
"""
import os
import re
import time
import uuid
import pytest
import requests


BACKEND_LOG = "/var/log/supervisor/backend.err.log"


def _tail_log(seconds_back: float = 30.0, max_bytes: int = 200_000) -> str:
    """Return the tail of the backend error log (where console-fallback emails are written)."""
    try:
        size = os.path.getsize(BACKEND_LOG)
        with open(BACKEND_LOG, "rb") as f:
            if size > max_bytes:
                f.seek(-max_bytes, os.SEEK_END)
            return f.read().decode("utf-8", errors="ignore")
    except FileNotFoundError:
        return ""


def _extract_reset_token_from_log(email: str, wait_seconds: float = 6.0) -> str | None:
    """Scan the backend log for the most recent reset link emitted after we
    triggered forgot-password for `email`. Falls back to any reset token if
    the email line itself isn't easy to anchor on."""
    deadline = time.time() + wait_seconds
    pattern_url = re.compile(r"/reset-password\?token=([A-Za-z0-9._\-]+)")
    last_token = None
    while time.time() < deadline:
        log = _tail_log()
        # Find all tokens; the password-reset block contains the email above the link.
        # Prefer a token in a block that mentions the email.
        # Naive but robust: split on the console-fallback banner.
        blocks = log.split("========== EMAIL (console fallback) ==========")
        for block in reversed(blocks):
            if email.lower() in block.lower():
                m = pattern_url.search(block)
                if m:
                    return m.group(1)
        # Fallback: any reset token in recent logs
        matches = pattern_url.findall(log)
        if matches:
            last_token = matches[-1]
        time.sleep(0.5)
    return last_token


# ---------- Case-insensitive register / login (P0 regression) ----------

class TestCaseInsensitiveEmail:
    def test_register_with_uppercase_email_returns_200(self, api_client, base_url):
        local = f"Mario.Rossi.{uuid.uuid4().hex[:6]}"
        email_mixed = f"{local}@Example.COM"
        r = api_client.post(
            f"{base_url}/api/auth/register",
            json={"email": email_mixed, "password": "TestPass123!", "role": "USER"},
        )
        assert r.status_code == 200, f"register w/ uppercase failed: {r.status_code} {r.text}"
        d = r.json()
        assert d["success"] is True
        # Persisted email must be lowercased
        assert d["user"]["email"] == email_mixed.lower()

    def test_login_is_case_insensitive(self, api_client, base_url):
        local = f"casey.{uuid.uuid4().hex[:6]}"
        original = f"{local}@Example.COM"
        password = "TestPass123!"
        # Register with mixed case
        r = api_client.post(
            f"{base_url}/api/auth/register",
            json={"email": original, "password": password, "role": "USER"},
        )
        assert r.status_code == 200, r.text

        # Login with three different casings -> all succeed and resolve to the same email
        for variant in (original.lower(), original.upper(), original):
            r = api_client.post(
                f"{base_url}/api/auth/login",
                json={"email": variant, "password": password},
            )
            assert r.status_code == 200, f"login w/ {variant!r} failed: {r.text}"
            assert r.json()["user"]["email"] == original.lower()


# ---------- Welcome email console fallback ----------

class TestWelcomeEmail:
    def test_welcome_email_logged_on_register(self, api_client, base_url):
        email = f"welcome.{uuid.uuid4().hex[:8]}@example.com"
        r = api_client.post(
            f"{base_url}/api/auth/register",
            json={"email": email, "password": "TestPass123!", "role": "USER"},
        )
        assert r.status_code == 200, r.text
        # Give the background email task time to write to the log
        deadline = time.time() + 6.0
        seen = False
        while time.time() < deadline:
            log = _tail_log()
            if "Welcome to NeoNoble Ramp" in log and email.lower() in log.lower():
                seen = True
                break
            time.sleep(0.4)
        assert seen, "Welcome email console-fallback line was not found in backend log"


# ---------- Forgot password (no enumeration + log fallback) ----------

class TestForgotPassword:
    GENERIC_MSG = "If that email is registered, a reset link is on its way."

    def test_forgot_password_existing_email_returns_generic_200(
        self, api_client, base_url, user_account
    ):
        r = api_client.post(
            f"{base_url}/api/auth/forgot-password",
            json={"email": user_account["email"]},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["success"] is True
        assert d["message"] == self.GENERIC_MSG

    def test_forgot_password_nonexistent_returns_same_body(self, api_client, base_url):
        r = api_client.post(
            f"{base_url}/api/auth/forgot-password",
            json={"email": f"nobody.{uuid.uuid4().hex[:8]}@example.com"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["success"] is True
        assert d["message"] == self.GENERIC_MSG

    def test_forgot_password_logs_reset_link_to_stdout(
        self, api_client, base_url, user_account
    ):
        r = api_client.post(
            f"{base_url}/api/auth/forgot-password",
            json={"email": user_account["email"]},
        )
        assert r.status_code == 200, r.text
        token = _extract_reset_token_from_log(user_account["email"], wait_seconds=8.0)
        assert token, "Reset-link token not found in backend log console fallback"
        assert len(token) > 20  # JWT-like


# ---------- Reset password ----------

class TestResetPassword:
    def _request_reset_token(self, api_client, base_url, email) -> str:
        r = api_client.post(
            f"{base_url}/api/auth/forgot-password", json={"email": email}
        )
        assert r.status_code == 200, r.text
        token = _extract_reset_token_from_log(email, wait_seconds=8.0)
        assert token, f"Could not extract reset token for {email} from backend log"
        return token

    def test_reset_password_success_and_login_with_new_password(
        self, api_client, base_url, user_account
    ):
        old_pw = user_account["password"]
        new_pw = "NewPass987!"
        token = self._request_reset_token(api_client, base_url, user_account["email"])

        # Reset succeeds
        r = api_client.post(
            f"{base_url}/api/auth/reset-password",
            json={"token": token, "new_password": new_pw},
        )
        assert r.status_code == 200, r.text
        assert r.json()["success"] is True

        # Login with NEW password succeeds
        r = api_client.post(
            f"{base_url}/api/auth/login",
            json={"email": user_account["email"], "password": new_pw},
        )
        assert r.status_code == 200, r.text

        # Login with OLD password fails 401
        r = api_client.post(
            f"{base_url}/api/auth/login",
            json={"email": user_account["email"], "password": old_pw},
        )
        assert r.status_code == 401
        assert "Invalid email or password" in r.json().get("detail", "")

    def test_reset_password_token_is_single_use(
        self, api_client, base_url, user_account
    ):
        token = self._request_reset_token(api_client, base_url, user_account["email"])
        r1 = api_client.post(
            f"{base_url}/api/auth/reset-password",
            json={"token": token, "new_password": "OneShotPw1!"},
        )
        assert r1.status_code == 200, r1.text
        # Second use of the SAME token must be rejected
        r2 = api_client.post(
            f"{base_url}/api/auth/reset-password",
            json={"token": token, "new_password": "Another9876!"},
        )
        assert r2.status_code == 400, r2.text
        assert "already been used" in (r2.json().get("detail") or "").lower() or \
               "no longer valid" in (r2.json().get("detail") or "").lower()

    def test_reset_password_invalid_token_returns_400(self, api_client, base_url):
        r = api_client.post(
            f"{base_url}/api/auth/reset-password",
            json={"token": "not.a.valid.jwt", "new_password": "Whatever123!"},
        )
        assert r.status_code == 400
        assert "Invalid or expired reset link" in r.json().get("detail", "")

    def test_reset_password_short_password_returns_400(
        self, api_client, base_url, user_account
    ):
        token = self._request_reset_token(api_client, base_url, user_account["email"])
        r = api_client.post(
            f"{base_url}/api/auth/reset-password",
            json={"token": token, "new_password": "short1"},
        )
        assert r.status_code == 400
        assert "8 characters" in r.json().get("detail", "")


# ---------- Change password (authenticated) ----------

class TestChangePassword:
    def test_change_password_success_and_login_with_new(
        self, api_client, base_url, user_account, user_authed_client
    ):
        new_pw = "BrandNewPw321!"
        r = user_authed_client.post(
            f"{base_url}/api/auth/change-password",
            json={
                "current_password": user_account["password"],
                "new_password": new_pw,
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["success"] is True

        # Login with new password works
        r = api_client.post(
            f"{base_url}/api/auth/login",
            json={"email": user_account["email"], "password": new_pw},
        )
        assert r.status_code == 200, r.text

    def test_change_password_wrong_current_returns_400(
        self, base_url, user_authed_client
    ):
        r = user_authed_client.post(
            f"{base_url}/api/auth/change-password",
            json={
                "current_password": "definitely-not-the-password",
                "new_password": "NewSecret123!",
            },
        )
        assert r.status_code == 400, r.text
        assert "Current password is incorrect" in r.json().get("detail", "")

    def test_change_password_without_auth_returns_401(self, api_client, base_url):
        r = api_client.post(
            f"{base_url}/api/auth/change-password",
            json={"current_password": "x", "new_password": "NewSecret123!"},
        )
        assert r.status_code in (401, 403)

    def test_change_password_short_new_password_returns_400(
        self, base_url, user_account, user_authed_client
    ):
        r = user_authed_client.post(
            f"{base_url}/api/auth/change-password",
            json={
                "current_password": user_account["password"],
                "new_password": "short1",
            },
        )
        assert r.status_code == 400, r.text
        assert "8 characters" in r.json().get("detail", "")
