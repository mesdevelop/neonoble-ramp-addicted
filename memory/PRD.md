# NeoNoble Ramp — Product Requirements Document

_Living document. Last updated: 2026-02_

## Original Problem Statement

Build a full-stack on/off-ramp platform for the **NeoNoble Ramp** product
(NeoNoble Technology Incorporation Limited):

- User authentication (email/password, JWT) for both the public Ramp app
  and a Dev Portal.
- Platform API key management with AES-256-GCM encryption and
  HMAC-SHA256 request signing.
- Public Ramp API endpoints (on-ramp / off-ramp quotes and execution).
- Real-time crypto pricing via CoinGecko, with NENO token fixed at
  €10,000.
- 60-minute quote TTL with locking to prevent double-spend.
- Real BSC blockchain integration: per-quote BEP-20 deposit address
  generation (HD wallet), on-chain transfer detection, automatic Stripe
  SEPA payout to the configured IBAN.
- Compliance: Transak widget staging integration for a UK compliance
  demo video.

## Architecture (current)

- **Frontend**: React + Tailwind, axios with silent-refresh interceptor.
  Component tree split into small sub-components + custom hooks.
- **Backend**: FastAPI + Motor (async MongoDB).
- **Auth**: JWT bearer in `Authorization` header; short-lived access
  token (15 min) + long-lived refresh token (7 days) stored in
  `localStorage`. See `SECURITY.md` for the hardening trade-offs and the
  planned `HttpOnly` cookie migration.
- **Blockchain**: web3.py polling on BSC; per-quote deposit address via
  BIP44 HD wallet derivation.
- **Payouts**: Stripe (live mode) — webhook route mounted at
  `/api/webhooks/stripe`. Live credentials still to be configured by the
  user before the first real payout.

## Implemented (✅)

- Full auth flow (register/login/`/me`/logout) ………………… DONE
- **Short-lived access token + refresh token + `/auth/refresh`** … DONE (2026-02)
- **Security response headers middleware** ………………………… DONE (2026-02)
- **Silent refresh axios interceptor** ……………………………… DONE (2026-02)
- **`/api/webhooks/stripe` route registered** …………………… DONE (2026-02)
- Dev Portal: API key create / reveal / revoke ………………… DONE
- HMAC middleware on Ramp APIs ………………………………………… DONE
- CoinGecko real-time pricing + NENO fixed at €10,000 ………… DONE
- 60-minute quote TTL + quote-lock ……………………………………… DONE
- HD-wallet BSC deposit address generation ………………………… DONE
- Blockchain listener wired into app lifespan ……………………… DONE
- Stripe payout service (live mode, no simulated fallback) … DONE (awaiting key)
- **Code-review fixes (2026-02)**:
  - useEffect / useCallback dependencies cleaned across 4 hooks
  - `console.error` wrapped in `NODE_ENV === 'development'`
  - `create_payout()` (147 lines) split into 4 helpers
  - `Dashboard.js` (424 lines → ~70 lines) + extracted hooks/components
  - `DevPortal.js` (441 lines → ~130 lines) + extracted hooks/components

## Backlog

### P0 — Pending live integration credentials
- 🔑 Add live `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
  `STRIPE_PAYOUT_IBAN`, `STRIPE_PAYOUT_BENEFICIARY_NAME` to backend
  `.env` and run a real end-to-end payout.
- 🔑 **Transak widget integration (staging)** — UK compliance demo.
  Scheduled for the next session. Needs `TRANSAK_API_KEY` (staging).

### P1 — Scheduled refactors
- 🍪 **HttpOnly cookie auth migration** (Option A) — scheduled for the
  next sprint, after Transak. See `SECURITY.md` for the full plan.
- Refactor `execute_offramp` / `execute_onramp` / `process_deposit_received`
  in `services/ramp_service.py` (97 / 75 / 70 lines).

### P2 — Nice-to-haves
- Admin endpoint to list/sync payouts.
- Right-after-signup landing: DEVELOPER role → `/dev` instead of `/dashboard`.
- Tighten `CORS_ORIGINS` from `*` to the allow-listed preview + prod URLs
  (paired with the cookie migration).

## Tech-stack Notes

- Originally requested PostgreSQL + Prisma; **MongoDB + Motor** chosen
  due to environment constraints — user accepted.
- All authenticated routes use the `/api` prefix; the bare-domain
  `/health` exists for Kubernetes liveness checks.

## Files of Reference (current)

```
/app/
├── backend/
│   ├── routes/        (auth, dev_portal, ramp_api, user_ramp, webhooks)
│   ├── services/      (auth, api_key, ramp, pricing, wallet, blockchain_listener, stripe_payout)
│   ├── utils/         (encryption, jwt_utils, password)
│   ├── tests/         (test_backend.py, conftest.py — 22 tests)
│   └── server.py      (lifespan: indexes + wallet + payout + blockchain polling)
├── frontend/
│   └── src/
│       ├── api/                 (index.js — token store + silent refresh)
│       ├── context/             (AuthContext.js)
│       ├── hooks/               (usePricing, useTransactions, useApiKeys, use-toast)
│       ├── components/
│       │   ├── dashboard/       (PriceDisplay, TransactionList, RampPanel, RampControls, QuoteCard, AlertBanner)
│       │   └── devportal/       (StatsBar, CreateKeyForm, CreatedKeyModal, ApiKeyList, ApiDocs)
│       └── pages/               (Home, Login, Signup, Dashboard, DevLogin, DevPortal)
├── memory/PRD.md
├── memory/test_credentials.md
├── SECURITY.md
└── test_reports/iteration_1.json   (22/22 pass)
```
