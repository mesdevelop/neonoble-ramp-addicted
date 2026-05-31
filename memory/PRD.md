# NeoNoble Ramp — Product Requirements Document

_Living document. Last updated: 2026-05 (iter_5 — CASP Sprint 1)_

## Original Problem Statement

Build a full-stack on/off-ramp platform for the **NeoNoble Ramp** product
(NeoNoble Technology Incorporation Limited):

- User authentication (email/password, JWT) for both the public Ramp app
  and a Dev Portal.
- Platform API key management (AES-256-GCM + HMAC-SHA256).
- Public Ramp API (on/off-ramp quotes + execution).
- Real-time pricing via CoinGecko, NENO token fixed at €10,000.
- 60-minute quote TTL with locking.
- Real BSC blockchain integration (per-quote BEP-20 deposit address +
  on-chain detection + Stripe SEPA payout).
- **Transak Widget STAGING integration** for UK compliance video.
- **PancakeSwap V2 on-chain swap** for the custom NENO token.
- **CASP Operating Stack (new)** — full 7-block MiCAR back-office to
  prepare CONSOB authorisation while staying compliant via Transak / PancakeSwap
  in shadow mode. Sumsub / Chainalysis / Fireblocks / Notabene integrated via
  swappable adapter pattern (MOCK by default, LIVE flag per provider).

## Architecture (current)

- **Frontend**: React + Tailwind. Silent-refresh axios. Custom hooks +
  small components. Ethers v6 for on-chain calls.
- **Backend**: FastAPI + Motor (async MongoDB). Resend for email.
- **Auth**: JWT — 15 min access + 7 day refresh in `localStorage`.
  Case-insensitive email throughout. Single-use password reset via JWT
  with persisted `jti` on user doc. Welcome + reset emails via Resend
  with console-fallback. See `SECURITY.md`.
- **Blockchain**: web3.py polling on BSC (server-side, NeoNoble internal
  flow). On-chain swap via ethers + window.ethereum (client-side,
  PancakeSwap flow).
- **Stripe**: webhook mounted at `/api/webhooks/stripe`. Live keys
  pending.
- **Transak**: `@transak/ui-js-sdk` v2 against `global-stg.transak.com`.
  Partner staging key configured. Server-to-server webhook with
  HMAC-SHA256 verification at `/api/transak/webhook`.

## Implemented (✅)

### Iteration 1 (auth hardening)
- 15-min access + 7-day refresh + `/auth/refresh` rotation
- Silent refresh interceptor
- Security response headers middleware
- `/api/webhooks/stripe` registered

### Iteration 2 (Transak STAGING base)
- `useWallet`, `WalletConnect`, `ComplianceBanner`, `TransakLauncher`
- Public `/transak` page (3 pillars + 3 CTAs + event stream)
- `TRANSAK_DEMO_WALKTHROUGH.md` + `_IT.md`

### Iteration 3 (P0 case-sensitivity + password flows)
- **P0 bug fix**: email case-insensitivity (`_normalize_email`) + null
  guard in register auto-login. Migration script normalised 63 users.
- `/forgot-password`, `/reset-password`, `/change-password` endpoints + pages
- Welcome email on register
- Resend integration with console fallback when no API key
- 24h reset token TTL, single-use via persisted `jti`
- `AuthShell` component, login `Forgot your password?` link,
  dashboard `Change Password` nav

### Iteration 4 (Transak partner key + PancakeSwap + Enterprise OTC)
- **Transak partner staging key** wired in `.env`; API secret kept
  server-side for webhook verification
- **Transak server-to-server webhook** `POST /api/transak/webhook` with
  HMAC-SHA256 verification accepting `x-signature`, `transak-signature`,
  or `x-transak-signature` headers (both `sha256=<hex>` and raw hex
  formats). Always returns 200 to avoid probe enumeration; logs verified
  flag on persisted event.
- **8-token catalogue** quick-pick on `/transak` (USDC/USDT/BNB on BSC,
  ETH and USDC on Ethereum, USDC and MATIC on Polygon, BTC on Bitcoin),
  with a clear "Add Custom Token" hint pointing to the Transak Partner
  Dashboard for NENO and other unlisted tokens.
- **PancakeSwap V2 on-chain swap** UI at the bottom of `/transak`:
  USDC ↔ NENO, debounced quote via `getAmountsOut`, slippage presets
  (0.5%/1%/3%), allowance handling, balance pre-check, BscScan tx link.
  Fully non-custodial — every tx is signed by user's wallet.
- **Enterprise OTC banner** on internal `/dashboard` separating the
  NeoNoble fixed-price OTC desk from the non-custodial Transak ramp.
- Resend API key configured (welcome + reset emails go out live).
- `TRANSAK_SUPPORTS_NENO=false` flag — flip to `true` after Transak's
  Asset Listing approval, and NENO appears automatically in the picker.

### Iteration 5 (current — CASP Operating Stack Sprint 1, 2026-05-31)
- **CASP back-office at `/admin/*`** — 9-section console (Dashboard,
  KYC/KYB, AML & Alerts, Treasury, OTC Desk B2B, Reporting, Customer
  Protection, Governance, Audit Log) gated by base role `ADMIN` +
  CASP role claims (`casp_admin_users` collection).
- **All 7 MiCAR operational blocks** wired end-to-end with REST API
  (`/api/casp/*`) and React UI (`/app/frontend/src/pages/Admin.js`):
  Block 1 KYC/KYB/Risk/Sanctions • Block 2 AML/Travel-Rule/SAR •
  Block 3 Custody/Reconciliation/Proof-of-Reserves • Block 4 B2B OTC
  desk with **4-eye approval > €50k** + best-execution evidence •
  Block 5 Reporting + Capital Adequacy snapshots • Block 6 Complaints
  (15-day SLA) + Asset Disclosures • Block 7 RBAC + Operational
  Incidents (DORA) + Conflicts of Interest.
- **Provider adapter pattern** in `services/casp/`: Sumsub (KYC),
  Chainalysis (KYT), Fireblocks (MPC custody), Notabene (Travel Rule).
  All four in MOCK mode by default; `<PROVIDER>_LIVE=true` env flag
  swaps each to live without code change.
- **Immutable WORM audit log** (`casp_audit_log`) — SHA-256 hash-chained,
  monotonic `sequence` index, `/api/casp/audit/verify` replays chain
  (CONSOB-grade evidence trail).
- **CASP RBAC** with 7 roles (ADMIN, MLRO, COMPLIANCE_OFFICER,
  RISK_OFFICER, TREASURY_OFFICER, OTC_TRADER, AUDITOR) +
  `require_casp_roles()` factory + 7 pre-built dependencies.
- **Seed script** `backend/scripts/seed_casp.py` creates 5 admin users,
  6 retail customers + 1 B2B institutional client, plus realistic
  sample data (KYC, AML, wallets, OTC, complaints, incidents, PoR).
- **CONSOB technical brief** at `/app/CASP_CONSOB_BRIEF.md` (EN + IT
  appendix) ready to attach to the authorisation application.
- Testing: 36/36 pytest backend + 6/6 frontend assertion groups
  (iteration_5.json). Legacy auth/Transak regression OK.

## Backlog

### P0 — Pending external action
- 🚨 **Reply to Transak compliance (Rahul Das)** — copy-paste the email body
  from `/app/TRANSAK_COMPLIANCE_REPLY.md` (English version) into Rahul's
  thread of 20/05/2026 to lift the KYB "on hold" status.
- 🌐 **Verify `neonoble-ramp.com` on Resend** (5 min) → unlock email
  delivery to arbitrary recipients (not just verified ones).
- 🆔 **Submit NENO Asset Listing request** to Transak Partner Dashboard
  with contract `0xeF3F5C1892A8d7A3304E4A15959E124402d69974`.
- 🎬 **Record the Transak compliance video** locally using `/transak` +
  `TRANSAK_DEMO_WALKTHROUGH_IT.md` (cannot be done by the AI agent).
- 🔑 Live Stripe keys (carried over).
- 🤝 **CASP Sprint 2 — Sumsub onboarding**: provide partner API keys to
  flip Sumsub adapter to LIVE (`SUMSUB_LIVE=true` + tokens in `.env`).

### P1 — Scheduled
- 🍪 HttpOnly cookie auth migration (Option A) — next sprint.
- 🏊 **Provide initial liquidity** to a NENO/USDC PancakeSwap V2 pool on
  BSC mainnet so the swap UI returns actual quotes.
- 🔨 Refactor `execute_offramp`/`execute_onramp`/`process_deposit_received`
  in `services/ramp_service.py`.
- 🧪 **CASP Sprint 3** — Chainalysis KYT contract + live integration.
- 🏦 **CASP Sprint 4** — Fireblocks workspace provisioning + live custody.
- 🌐 **CASP Sprint 5** — Notabene Travel Rule live.
- 🪪 **Sub-admin base role** (`CASP_OPERATOR`) — to actually enforce
  CASP-role gating on specialists (today they are base=ADMIN per seed so
  super-admin bypass kicks in; the 4-eye guard is the real safety net but
  having proper role isolation is cleaner).

### P2 — Nice-to-haves
- Move Transak token catalogue to `.env` JSON (no redeploy)
- Admin endpoint listing all Transak webhook events
- Transak order-status push from webhook into user's notification panel
- 2FA TOTP for DEVELOPER + ADMIN roles
- Export audit log as a signed PDF (Adobe LTV/PAdES) for off-chain archival

## Files of Reference

```
/app/
├── backend/
│   ├── routes/        (auth, dev_portal, ramp_api, user_ramp, webhooks, transak)
│   ├── services/      (auth, api_key, ramp, pricing, wallet, blockchain_listener,
│   │                   stripe_payout, transak, email)
│   ├── utils/         (encryption, jwt_utils [+password_reset], password)
│   ├── tests/         (test_backend.py, test_transak.py, test_password_flows.py,
│   │                   conftest.py — 48 pytest tests, 1 expected skip)
│   ├── scripts/       (normalise_user_emails.py — idempotent, already ran)
│   └── server.py
├── frontend/
│   └── src/
│       ├── api/                 (index.js with silent refresh, transak.js)
│       ├── context/             (AuthContext.js)
│       ├── hooks/               (usePricing, useTransactions, useApiKeys,
│       │                         useWallet, use-toast)
│       ├── lib/                 (pancakeswap.js — ethers v6 swap helpers)
│       ├── components/
│       │   ├── auth/            (AuthShell)
│       │   ├── dashboard/       (PriceDisplay, TransactionList, RampPanel, …)
│       │   ├── devportal/       (StatsBar, CreateKeyForm, CreatedKeyModal, …)
│       │   └── transak/         (ComplianceBanner, WalletConnect,
│       │                         TransakLauncher, PancakeSwapPanel)
│       └── pages/               (Home, Login, Signup, Dashboard, DevLogin,
│                                 DevPortal, TransakDemo, ForgotPassword,
│                                 ResetPassword, ChangePassword)
├── memory/PRD.md
├── memory/test_credentials.md
├── SECURITY.md
├── TRANSAK_DEMO_WALKTHROUGH.md  + _IT.md
└── test_reports/
    ├── iteration_1.json   # 22/22 auth hardening
    ├── iteration_2.json   # 29/29 Transak STAGING
    ├── iteration_3.json   # 43/43 + 8/8 case-sensitivity + password reset
    └── iteration_4.json   # 48/48 webhook HMAC + PancakeSwap + Enterprise OTC
```

## Compliance pillar enforcement (Transak)

| Pillar | Where it's enforced |
|---|---|
| User-initiated Only | Buy/Sell/Swap buttons + PancakeSwap UI disabled until `wallet.address` is set. No backend endpoint creates a trade. |
| No Fund Intermediation | `/api/transak` only `GET /config` + `POST /events` + signed-only `POST /webhook`. No transfer/payout/order endpoint. |
| Direct Delivery | Widget URL built with `walletAddress=<user_addr>` + `disableWalletAddressForm=true`. PancakeSwap router invoked directly from user's wallet. |

## Tech-stack Notes

- MongoDB + Motor (user accepted, instead of PostgreSQL+Prisma).
- All authenticated routes use the `/api` prefix; bare-domain `/health`
  for Kubernetes liveness checks.
- Transak SDK: `@transak/ui-js-sdk` v2 — widget opened via popup window
  (NOT iframe) to bypass `frame-ancestors` for the staging preview URL.
- Ethers v6 for client-side on-chain calls.
- Resend v2.30.1 for transactional email.
