# Test Credentials

The backend test suite **creates unique users dynamically** on every run via
`POST /api/auth/register`. No persistent seeded user is required.

## How tests create users

- Email: `TEST_<uuid>@example.com` (unique per run)
- Password: `TestPass123!`
- Role: `USER` or `DEVELOPER` (depending on the flow under test)

## Manual smoke account (optional)

If you need to log in by hand, create one via:

```bash
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2 | tr -d '"')
curl -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@neonoble.test","password":"TestPass123!","role":"DEVELOPER"}'
```

Then log in at `${REACT_APP_BACKEND_URL}/login` with the same email + password.

## Integration credentials (NOT in this file)

- `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` — **not configured yet**.
  User scheduled live Stripe testing for a future sprint. Webhook route is
  mounted and handles missing/bogus signatures gracefully.
- `TRANSAK_API_KEY` — pending (staging key will be added during the Transak
  widget integration task scheduled for the next session).
