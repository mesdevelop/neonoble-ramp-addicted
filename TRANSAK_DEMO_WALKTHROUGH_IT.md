# Walkthrough Demo Transak — Copione Video

**Obiettivo:** registrare un video end-to-end di 45–90 secondi per il team
di compliance UK di Transak. Dimostra un flusso completamente
non-custodial: **Onboarding → Connessione Wallet → Transak → Wallet → Interazione.**

**URL Demo:** `${REACT_APP_BACKEND_URL}/transak`
(attualmente: `https://neonoble-ramp.preview.emergentagent.com/transak`)

**Token mostrato:**
- **Intento primario:** NENO (BEP-20, `0xeF3F5C1892A8d7A3304E4A15959E124402d69974`)
- **Fallback in staging:** USDC su BSC — NENO non è ancora listato nel
  catalogo staging di Transak. La UI lo dichiara esplicitamente. Basta
  flippare `TRANSAK_SUPPORTS_NENO=true` in `backend/.env` nel momento in
  cui Transak abiliterà NENO, e il widget cambierà automaticamente.

**Ambiente:** Transak `STAGING` (`global-stg.transak.com`).

---

## Pre-flight (da fare una volta sola, OFF-camera)

1. Installa **MetaMask** nel browser che userai per la registrazione.
2. Crea o importa un wallet **usa-e-getta** (NON usare le tue chiavi di produzione).
3. Aggiungi **BNB Smart Chain (mainnet)** al wallet — la pagina ha un
   pulsante "Switch to BNB Smart Chain" che te lo aggiunge in automatico.
4. Carica il wallet con una manciata di BNB e un piccolo saldo di USDC su
   BSC se vuoi che il flusso SELL arrivi fino allo schermo finale. Il
   widget staging accetta KYC di prova, ma per la SELL serve saldo reale.
5. Apri uno screen recorder (OBS, QuickTime, Loom, …) a 1080p.

---

## Copione on-camera (60–75 secondi)

| t | Cosa si vede | Cosa dire (voiceover suggerito) |
|---|---|---|
| 0–4s | Home page → click su **Get Started → Login** → arrivi sulla Dashboard | "Questo è NeoNoble Ramp. La demo di compliance è dietro la tab **Transak Demo**." |
| 4–8s | Click su **Transak Demo** nell'header della Dashboard → si carica la pagina `/transak` | "Apriamo la route dedicata, non-custodial." |
| 8–18s | Passa sopra alle tre card dei pillar (User-initiated · No Fund Intermediation · Direct Delivery) | "Tre pillar: user-initiated only, no fund intermediation, direct delivery — resi visibili direttamente in pagina." |
| 18–25s | Click su **Connect Wallet** → prompt di MetaMask → approva → appare la card verde "Wallet connected" | "Step 1: l'utente connette esplicitamente il proprio wallet. Questo indirizzo è l'unica destinazione su cui Transak consegnerà i fondi." |
| 25–30s | Se la chain non è BSC, click su **Switch to BNB Smart Chain** | "Passiamo a BNB Smart Chain — la rete su cui vive NENO." |
| 30–40s | Click su **Buy Crypto (On-Ramp)** → il widget Transak si apre con l'indirizzo pre-compilato e **disabilitato** | "Step 2: Buy. Il widget Transak si apre con l'indirizzo del wallet dell'utente, bloccato tramite `disableWalletAddressForm` — non possono ridirigere la consegna. Per ora il token è USDC su BSC; NENO sarà attivato non appena Transak whitelistarà il nostro contratto." |
| 40–50s | Chiudi il widget. Click su **Sell Crypto (Off-Ramp)** → il widget riapre in modalità SELL | "Step 3: Sell. Stesso wallet, stesso lock. L'utente firma il trasferimento in uscita personalmente — NeoNoble non ha alcuna autorità di firma." |
| 50–58s | Chiudi, poi click su **Swap (Buy/Sell)** → vedi entrambe le tab disponibili | "Step 4: una tab Swap unificata commuta tra BUY e SELL con `productsAvailed=BUY,SELL`." |
| 58–70s | Scrolla fino alla card **Transak event stream** che mostra `TRANSAK_WIDGET_INITIALISED`, `…OPEN`, `…CLOSE` | "Ogni evento dell'SDK Transak è loggato client-side e inoltrato al nostro backend per audit — mai come trigger di trade." |
| 70–75s | Apri la sezione collassata **Widget configuration** che rivela il JSON di config | "Ecco la config completa, sola lettura: ambiente STAGING, network BSC, fiat EUR, walletAddress = indirizzo dell'utente, `disableWalletAddressForm=true`. Fine." |

---

## Mapping Pillar → UI

| Pillar | Dove è imposto | Cosa si vede in camera |
|---|---|---|
| **User-initiated Only** | I pulsanti Buy/Sell/Swap sono disabilitati fino a quando `wallet.address` non è valorizzato in `useWallet`. Nessun endpoint backend crea trade. | I pulsanti sono visibilmente grigi finché "Connect Wallet" non riesce; la nota disabilitata recita "Connect your wallet first to enable Buy/Sell/Swap." |
| **No Fund Intermediation** | Il backend espone solo `GET /api/transak/config` (read-only) e `POST /api/transak/events` (solo log). Nessun endpoint di transfer, payout o custody. | Il JSON della sezione "Widget configuration" mostra `non_custodial: true` e l'oggetto `compliance`. |
| **Direct Delivery** | L'URL del widget è costruito con `walletAddress=<indirizzo_utente>` + `disableWalletAddressForm=true` + `partnerCustomerId=<indirizzo_utente>`. | Dentro il modal Transak, il campo wallet di destinazione è pre-compilato e non editabile. La card "Wallet connected" mostra esattamente lo stesso indirizzo. |

---

## Imprevisti tipici durante la registrazione

- **No injected wallet detected:** la pagina mostra un warning giallo.
  Installa MetaMask e ricarica la pagina prima di registrare.
- **I pulsanti restano grigi:** il wallet è connesso ma sulla rete sbagliata.
  Click su **Switch to BNB Smart Chain**.
- **Il widget si apre con un token diverso:** il catalogo staging
  occasionalmente rimappa `cryptoCurrencyCode`. Verifica nell'URL dentro
  l'iframe che ci sia `cryptoCurrencyCode=USDC` (o `NENO` una volta
  supportato). Se non c'è, cambia `TRANSAK_FALLBACK_TOKEN` in
  `backend/.env` con un altro token listato (es. `USDT`) e riavvia il backend.
- **Errore `apiKey` non configurato:** manca `TRANSAK_API_KEY` in
  `backend/.env`. Settalo (di default: la staging key pubblica dai docs
  Transak) e fai `sudo supervisorctl restart backend`.

---

## Tear-down (da fare DOPO la registrazione)

- Disconnetti il wallet usa-e-getta da MetaMask → "Connected sites" →
  Rimuovi `neonoble-ramp.preview.emergentagent.com`.
- Sposta o distruggi il wallet usa-e-getta — non riutilizzarlo in produzione.

---

## Endpoint backend usati da questo flusso

```
GET  /api/transak/config        # config pubblica del widget (api_key, env, network, fiat, flag compliance)
POST /api/transak/events        # logging osservazionale degli eventi dal browser dell'utente
GET  /api/transak/events?wallet_address=0x…   # rileggi gli eventi di quel wallet
```

Nessuno degli endpoint sopra crea, instrada o regola un trade. Il widget
Transak gira interamente nel browser dell'utente e regola i fondi
direttamente sul wallet dell'utente.
