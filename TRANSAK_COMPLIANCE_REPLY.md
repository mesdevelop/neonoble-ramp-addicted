# Reply to Transak Compliance — Rahul Das

> Copy-paste the **English version** as the email body. The **Italian version** below is for your personal reference / archive only. 
> Reply directly to Rahul's thread (subject: *"Dear Massimo, Thank you for your detailed response…"*) so that the KYB review resumes on the existing application without resubmission.

---

## ✉️ ENGLISH VERSION (send this)

**Subject:** Re: NeoNoble × Transak — KYB Clarifications & Integration Confirmation

---

Dear Rahul,

Thank you for following up, and apologies for the delayed reply on my side. Please find below the explicit, point-by-point confirmations you requested regarding the NeoNoble integration model. The platform is built to align fully with Transak's supported integration framework, and every item below is already enforced both in the codebase and in the production UI.

**1. User-initiated transactions & explicit wallet signatures**
I confirm that every trading and swap action on NeoNoble is **fully user-initiated**. The user must (a) connect their own self-custody wallet (MetaMask / WalletConnect), (b) explicitly click the action button, and (c) sign the resulting transaction in their wallet. No transaction is ever broadcast on the user's behalf, and no signing key is ever held, derived, or accessed by NeoNoble's backend.

**2. No automated execution or backend-controlled processing**
I confirm that NeoNoble's backend **does not execute, schedule, batch, or auto-trigger** any trading or swap transaction. The backend's role is strictly limited to: (i) serving the frontend, (ii) generating the secure Transak widget URL via the official `POST /partners/api/v2/auth/session` server-side endpoint, and (iii) reading on-chain data for display purposes. All state changes on-chain originate exclusively from the user's wallet.

**3. No fund routing, aggregation, or intermediation**
I confirm that NeoNoble **never receives, routes, aggregates, or intermediates user funds** during on-ramp, off-ramp, or swap operations. Fiat flows directly from the user to Transak (and its licensed liquidity partners) via Transak's own infrastructure; crypto flows directly from Transak to the user's self-custody wallet. NeoNoble is not a party to the settlement at any stage.

**4. Direct delivery to user-controlled wallets**
I confirm that all assets purchased via Transak are delivered **directly to the wallet address the user connected on our frontend**. The `walletAddress` parameter passed to the Transak widget is set verbatim from `window.ethereum.selectedAddress` (the address the user authenticated with), and the parameter `disableWalletAddressForm=true` is enforced so the user cannot modify it inside the widget — guaranteeing the destination is the connected self-custody address and nothing else.

**5. No platform-controlled wallets or internal balance system**
I confirm that NeoNoble **operates no custodial wallets, hot wallets, omnibus accounts, or internal balance ledgers** for retail users. There is no user balance on the platform — the "balance" displayed in the UI is simply a live `eth_getBalance` / ERC-20 `balanceOf` read against the user's own address on BSC / Ethereum / Polygon. Users keep 100% control of their private keys at all times.

**6. End-to-end user experience walkthrough**
The complete user journey is as follows:
1. **Onboarding** — User lands on `/transak`, accepts the cookie/Terms notice, and connects their self-custody wallet (MetaMask / WalletConnect). No KYC is collected by NeoNoble; KYC is performed exclusively by Transak inside the widget.
2. **Token selection** — User picks the asset (USDC / USDT / BNB / ETH / MATIC / BTC). NENO is currently pending listing — for it we use a Pancake­Swap router as a separate, fully on-chain, non-custodial DEX swap (the user signs the swap tx in their wallet).
3. **Transak interaction** — Our backend calls `POST /partners/api/v2/auth/session` with the partner API key and the user's connected wallet address, then returns a one-time signed `widgetUrl`. The frontend opens it in a **separate popup window** (never an iframe), so the entire fiat → KYC → settlement flow occurs inside Transak's own domain.
4. **Settlement** — Transak settles crypto directly to the user's connected wallet on the chosen chain. NeoNoble receives only a webhook event (HMAC-verified) for analytics/UX state — funds never touch our infrastructure.
5. **Post-transaction** — The frontend re-reads the on-chain balance and, if the user wishes, the user can self-initiate a Pancake­Swap swap, again signing every step in their own wallet.

For your convenience, the live staging page `/transak` of our application explicitly publishes these four pillars in the UI — *Non-custodial by design • User-initiated only • No fund intermediation • Direct delivery* — and they are observable in the screenshot attached to this email.

I am at your full disposal for any further clarification or written attestation you may require to close the KYB review. Looking forward to resuming the assessment.

Best regards,
Massimo Fornara

---

## 🇮🇹 ITALIAN VERSION (personal reference)

**Oggetto:** Re: NeoNoble × Transak — Chiarimenti KYB & Conferma del modello di integrazione

---

Gentile Rahul,

grazie per il sollecito e mi scuso per il ritardo nella mia risposta. Di seguito trovi le conferme esplicite, punto per punto, che mi hai richiesto in merito al modello di integrazione di NeoNoble. La piattaforma è progettata per essere pienamente conforme al framework di integrazione supportato da Transak, e ciascuno dei punti seguenti è già implementato sia a livello di codice sia nell'interfaccia utente in produzione.

**1. Transazioni user-initiated e firma esplicita del wallet**
Confermo che ogni operazione di trading e swap su NeoNoble è **completamente avviata dall'utente**. L'utente deve (a) connettere il proprio wallet self-custody (MetaMask / WalletConnect), (b) cliccare esplicitamente sul pulsante d'azione e (c) firmare la transazione risultante all'interno del proprio wallet. Nessuna transazione viene mai trasmessa al posto dell'utente, e nessuna chiave privata viene mai detenuta, derivata o letta dal backend NeoNoble.

**2. Nessuna esecuzione automatica o backend-controlled**
Confermo che il backend di NeoNoble **non esegue, non pianifica, non aggrega in batch e non auto-avvia** alcuna transazione di trading o swap. Il ruolo del backend è strettamente limitato a: (i) servire il frontend, (ii) generare l'URL sicuro del widget Transak tramite l'endpoint server-side ufficiale `POST /partners/api/v2/auth/session`, (iii) leggere dati on-chain solo a scopo di visualizzazione. Tutti i cambi di stato on-chain originano esclusivamente dal wallet dell'utente.

**3. Nessun routing, aggregazione o intermediazione di fondi**
Confermo che NeoNoble **non riceve, non instrada, non aggrega e non intermedia mai fondi degli utenti** durante operazioni di on-ramp, off-ramp o swap. Il flusso fiat va direttamente dall'utente a Transak (e ai suoi partner di liquidità autorizzati) tramite l'infrastruttura di Transak; il flusso crypto va direttamente da Transak al wallet self-custody dell'utente. NeoNoble non è mai parte del settlement in nessuna fase.

**4. Consegna diretta a wallet sotto controllo dell'utente**
Confermo che tutti gli asset acquistati tramite Transak vengono consegnati **direttamente all'indirizzo wallet connesso dall'utente sul nostro frontend**. Il parametro `walletAddress` passato al widget Transak è impostato in modo identico al valore restituito da `window.ethereum.selectedAddress` (l'indirizzo con cui l'utente si è autenticato), e il parametro `disableWalletAddressForm=true` è forzato in modo che l'utente non possa modificarlo dentro il widget — garantendo che la destinazione sia esclusivamente l'indirizzo self-custody connesso.

**5. Nessun wallet della piattaforma né sistema di saldo interno**
Confermo che NeoNoble **non gestisce wallet custodial, hot wallet, conti omnibus o registri di saldo interni** per gli utenti retail. Sulla piattaforma non esiste alcun saldo utente — il "balance" mostrato in UI è semplicemente una lettura live di `eth_getBalance` / `balanceOf` ERC-20 sull'indirizzo dell'utente su BSC / Ethereum / Polygon. Gli utenti mantengono il 100% del controllo delle proprie chiavi private in ogni momento.

**6. Walkthrough end-to-end dell'esperienza utente**
Il percorso utente completo è il seguente:
1. **Onboarding** — L'utente apre `/transak`, accetta cookie/Termini e connette il proprio wallet self-custody (MetaMask / WalletConnect). NeoNoble non raccoglie alcun KYC; il KYC è eseguito esclusivamente da Transak dentro il widget.
2. **Selezione del token** — L'utente seleziona l'asset (USDC / USDT / BNB / ETH / MATIC / BTC). NENO è attualmente in pending di listing — per esso utilizziamo il router PancakeSwap come swap DEX separato, completamente on-chain e non-custodial (l'utente firma la tx di swap nel proprio wallet).
3. **Interazione con Transak** — Il nostro backend chiama `POST /partners/api/v2/auth/session` con la partner API key e l'indirizzo wallet connesso dall'utente, e restituisce un `widgetUrl` firmato monouso. Il frontend lo apre in una **finestra popup separata** (mai in iframe), così l'intero flusso fiat → KYC → settlement avviene all'interno del dominio Transak.
4. **Settlement** — Transak invia crypto direttamente al wallet connesso dall'utente sulla chain scelta. NeoNoble riceve solo un evento webhook (verificato in HMAC) a fini di analytics/stato UX — i fondi non passano mai attraverso la nostra infrastruttura.
5. **Post-transazione** — Il frontend rilegge il balance on-chain e, se lo desidera, l'utente può avviare autonomamente uno swap su PancakeSwap, firmando di nuovo ogni step dentro il proprio wallet.

Per tua comodità, la pagina staging `/transak` della nostra applicazione pubblica esplicitamente in UI i quattro pillar — *Non-custodial by design • User-initiated only • No fund intermediation • Direct delivery* — visibili nello screenshot allegato a questa email.

Resto a tua completa disposizione per ogni ulteriore chiarimento o attestazione scritta che ti possa servire per chiudere la review KYB. Resto in attesa della ripresa della valutazione.

Cordiali saluti,
Massimo Fornara
