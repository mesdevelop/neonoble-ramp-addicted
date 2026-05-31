# Test Credentials

Tests register ephemeral users dynamically — no persistent seeded account is required.

## How tests create users
- Email: `TEST_<uuid>@example.com` (unique per run)
- Password: `TestPass123!`
- Role: `USER` or `DEVELOPER`

## Manual smoke account (optional)
```bash
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2 | tr -d '"')
curl -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@neonoble.test","password":"TestPass123!","role":"DEVELOPER"}'
```

## Password reset flow (no Resend key set)
With `RESEND_API_KEY` empty, the reset email is logged to backend stdout.
Extract the token like this:

```bash
tail -n 80 /var/log/supervisor/backend.err.log | grep -oE 'reset-password\?token=[A-Za-z0-9._-]+' | tail -1
```

## Integration credentials (NOT in this file)
- `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` — not configured yet.
- `TRANSAK_API_KEY` — currently the public staging key from Transak docs
  (`8be07021-...`). Replace with the user's partner staging key when issued.
- `RESEND_API_KEY` — empty by design; emails fall back to console logging.
