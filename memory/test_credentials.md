# Test Credentials

Tests register ephemeral users dynamically — no persistent seeded account is required.

## How tests create users
- Email: `TEST_<uuid>@example.com` (unique per run)
- Password: `TestPass123!`
- Role: `USER` or `DEVELOPER`

## CASP back-office accounts (seeded by `backend/scripts/seed_casp.py`)
All passwords: **`CaspAdmin!2026`**

| Email | Base role | CASP roles | Department |
|---|---|---|---|
| `casp-admin@neonoble.example.com` | ADMIN | ADMIN (all) | Executive |
| `casp-mlro@neonoble.example.com` | ADMIN | MLRO, COMPLIANCE_OFFICER | Compliance |
| `casp-trader@neonoble.example.com` | ADMIN | OTC_TRADER | Trading |
| `casp-risk@neonoble.example.com` | ADMIN | RISK_OFFICER | Risk |
| `casp-treasury@neonoble.example.com` | ADMIN | TREASURY_OFFICER | Treasury |
| `institutional@bigcorp.example.com` | USER | — (B2B demo client) | — |

Login → navigate to `/admin` for the CASP Operations Console.

Re-seed at any time:
```bash
cd /app/backend && python scripts/seed_casp.py
```

## Manual smoke account (optional)
```bash
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2 | tr -d '"')
curl -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@neonoble.example.com","password":"TestPass123!","role":"DEVELOPER"}'
```

## Password reset flow (no Resend key set)
With `RESEND_API_KEY` empty, the reset email is logged to backend stdout.
```bash
tail -n 80 /var/log/supervisor/backend.err.log | grep -oE 'reset-password\?token=[A-Za-z0-9._-]+' | tail -1
```

## Integration credentials (NOT in this file)
- `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` — not configured yet.
- `TRANSAK_API_KEY` — currently the public staging key from Transak docs
  (`8be07021-...`). Replace with the user's partner staging key when issued.
- `RESEND_API_KEY` — empty by design; emails fall back to console logging.
- `SUMSUB_APP_TOKEN` / `SUMSUB_SECRET_KEY` — empty; adapter in MOCK mode.
  Set `SUMSUB_LIVE=true` + keys to switch.
- `CHAINALYSIS_API_KEY` — empty; KYT adapter in MOCK mode. Set `CHAINALYSIS_LIVE=true` + key.
- `FIREBLOCKS_API_KEY` + `FIREBLOCKS_PRIVATE_KEY` — empty; custody adapter in MOCK mode.
  Set `FIREBLOCKS_LIVE=true` + creds.
- `NOTABENE_API_KEY` + `NOTABENE_CLIENT_ID` — empty; TR adapter in MOCK mode. Set `NOTABENE_LIVE=true` + key.
