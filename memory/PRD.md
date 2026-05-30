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
- Real-time crypto pricing via CoinGecko, with NENO token fixed at €10,000.
- 60-minute quote TTL with locking to prevent double-spend.
- Real BSC blockchain integration: per-quote BEP-20 deposit address,
  on-chain transfer detection, automatic Stripe SEPA payout.
- **Compliance: Transak Widget STAGING integration for the UK compliance
  walkthrough video.** Three pillars must be visibly enforced:
  *User-initiated Only*, *No Fund Intermediation*, *Direct Delivery*.

## Architecture (current)

- **Frontend**: React + Tailwind, axios with silent-refresh interceptor.
  Small, single-responsibility components + custom hooks.
- **Backend**: FastAPI + Motor (async MongoDB).
- **Auth**: JWT bearer — 15 min access + 7 day refresh in `localStorage`
  (`SECURITY.md` documents the planned `HttpOnly` cookie migration).
- **Blockchain**: web3.py polling on BSC; per-quote deposit address via
  BIP44 HD wallet derivation.
- **Payouts (NeoNoble Ramp internal flow)**: Stripe (live mode), webhook
  mounted at `/api/webhooks/stripe`. Live key still to be configured.
- **Transak (compliance demo flow)**: `@transak/ui-js-sdk` v2 against
  `global-stg.transak.com`. Strictly non-custodial: the user connects
  their own injected wallet, the address is passed verbatim to Transak
  with `disableWalletAddressForm=true`, the backend has **no**
  trade-creation endpoint (only `GET /config` and `POST /events`).

## Implemented (✅)

- Full auth flow (register/login/`/me`/logout) ………………… DONE
- Short-lived access token + refresh + `/auth/refresh` ……… DONE (2026-02)
- Security response headers middleware ………………………………… DONE (2026-02)
- Silent refresh axios interceptor ……………………………………… DONE (2026-02)
- `/api/webhooks/stripe` route registered ………………………… DONE (2026-02)
- **Transak STAGING integration** ………………………………………… DONE (2026-02)
  - `/api/transak/config`, `/api/transak/events` (log + readback)
  - `useWallet` hook (window.ethereum, BSC chain-switch)
  - `WalletConnect`, `ComplianceBanner`, `TransakLauncher` components
  - Public `/transak` page with three pillar cards, three CTA buttons,
    event stream + collapsed config JSON for the video
  - USDC-on-BSC fallback until Transak whitelists NENO
  - `TRANSAK_DEMO_WALKTHROUGH.md` 45–90s video script
- Dev Portal: API key create / reveal / revoke ………………… DONE
- HMAC middleware on Ramp APIs ………………………………………… DONE
- CoinGecko real-time pricing + NENO fixed at €10,000 ………… DONE
- 60-minute quote TTL + quote-lock ……………………………………… DONE
- HD-wallet BSC deposit address generation ………………………… DONE
- Blockchain listener wired into app lifespan ……………………… DONE
- Stripe payout service (live mode, no simulated fallback) … DONE (awaiting key)
- Code-review fixes (2026-02): hook deps, `console.error` dev-only,
  `create_payout` split into 4 helpers, `Dashboard.js` / `DevPortal.js`
  reduced to thin orchestrators with extracted hooks + sub-components

## Backlog

### P0 — Pending live integration credentials
- 🎬 **Record the Transak walkthrough video** from
  `${REACT_APP_BACKEND_URL}/transak` using a disposable MetaMask wallet.
  Script: `/app/TRANSAK_DEMO_WALKTHROUGH.md`. ETA after MetaMask install:
  ~5 min.
- 🔑 Add live `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
  `STRIPE_PAYOUT_IBAN`, `STRIPE_PAYOUT_BENEFICIARY_NAME` to backend
  `.env` and run a real end-to-end payout (was deferred from previous session).

### P1 — Scheduled refactors
- 🍪 **HttpOnly cookie auth migration** (Option A) — scheduled for the
  next sprint, after compliance video. See `SECURITY.md`.
- Refactor `execute_offramp` / `execute_onramp` / `process_deposit_received`
  in `services/ramp_service.py`.
- Flip `TRANSAK_SUPPORTS_NENO=true` the moment Transak whitelists
  `0xeF3F5C1892A8d7A3304E4A15959E124402d69974` on staging.

### P2 — Nice-to-haves
- Admin endpoint to list/sync payouts.
- After signup with DEVELOPER role → land on `/dev` instead of `/dashboard`.
- Tighten `CORS_ORIGINS` from `*` to an allow-list (paired with the
  cookie migration).
- Transak webhook receiver (server-to-server order updates) to
  complement the client-side event log.

## Tech-stack Notes

- Originally requested PostgreSQL + Prisma; **MongoDB + Motor** chosen
  due to environment constraints — user accepted.
- All authenticated routes use the `/api` prefix; bare-domain `/health`
  for Kubernetes liveness checks.
- Transak SDK: `@transak/ui-js-sdk` v2 (NOT the older `@transak/transak-sdk`).
  Widget initialized via `widgetUrl` query-string composition.

## Compliance pillar enforcement (Transak)

| Pillar | Where it's enforced |
|---|---|
| User-initiated Only | Buy/Sell/Swap buttons disabled until `wallet.address` is set. No backend endpoint creates a trade. |
| No Fund Intermediation | `/api/transak` only exposes `GET /config` and `POST /events`. No transfer/payout/order endpoint. Verified via 10 forbidden-path 404 probes in `tests/test_transak.py`. |
| Direct Delivery | Widget URL built with `walletAddress=<user_addr>` + `disableWalletAddressForm=true`. The address shown in the green "Wallet connected" card is the same one Transak receives. |

## Files of Reference (current)

```
/app/
├── backend/
│   ├── routes/        (auth, dev_portal, ramp_api, user_ramp, webhooks, transak)
│   ├── services/      (auth, api_key, ramp, pricing, wallet, blockchain_listener,
│   │                   stripe_payout, transak)
│   ├── utils/         (encryption, jwt_utils, password)
│   ├── tests/         (test_backend.py, test_transak.py, conftest.py)
│   └── server.py
├── frontend/
│   └── src/
│       ├── api/                 (index.js, transak.js)
│       ├── context/             (AuthContext.js)
│       ├── hooks/               (usePricing, useTransactions, useApiKeys,
│       │                         useWallet, use-toast)
│       ├── components/
│       │   ├── dashboard/       (PriceDisplay, TransactionList, RampPanel, …)
│       │   ├── devportal/       (StatsBar, CreateKeyForm, CreatedKeyModal, …)
│       │   └── transak/         (ComplianceBanner, WalletConnect, TransakLauncher)
│       └── pages/               (Home, Login, Signup, Dashboard, DevLogin,
│                                 DevPortal, TransakDemo)
├── memory/PRD.md
├── memory/test_credentials.md
├── SECURITY.md
├── TRANSAK_DEMO_WALKTHROUGH.md   # 45-90s video script
└── test_reports/
    ├── iteration_1.json   # auth-hardening + refactor — 22/22 pass
    └── iteration_2.json   # Transak STAGING — 29/29 pass
```
