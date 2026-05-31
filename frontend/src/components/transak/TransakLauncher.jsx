import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowUpRight, ArrowDownRight, RefreshCw, Loader2, ExternalLink } from 'lucide-react';
import { transakApi } from '../../api/transak';

const STG_WIDGET_BASE = 'https://global-stg.transak.com';
const PROD_WIDGET_BASE = 'https://global.transak.com';

const STG_ORIGIN = 'https://global-stg.transak.com';
const PROD_ORIGIN = 'https://global.transak.com';

const buildWidgetUrl = (config, walletAddress, productsAvailed) => {
  const base = config.environment === 'PRODUCTION' ? PROD_WIDGET_BASE : STG_WIDGET_BASE;
  const cryptoCurrencyCode = config.supports_neno ? 'NENO' : config.fallback_token || 'USDC';
  const params = new URLSearchParams({
    apiKey: config.api_key,
    environment: config.environment || 'STAGING',
    productsAvailed,
    cryptoCurrencyCode,
    network: config.network || 'bsc',
    walletAddress,
    disableWalletAddressForm: 'true',
    hideMenu: 'true',
    themeColor: '7c3aed',
    defaultFiatCurrency: config.fiat_currency || 'EUR',
    referrerDomain: config.referrer_domain || window.location.host,
    partnerCustomerId: walletAddress,
  });
  return `${base}?${params.toString()}`;
};

const PRODUCT_MAP = {
  BUY: 'BUY',
  SELL: 'SELL',
  SWAP: 'BUY,SELL',
};

const POPUP_FEATURES = 'width=480,height=720,resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no,location=no';

export const TransakLauncher = ({ config, walletAddress, isBSC, onEvent }) => {
  const [opening, setOpening] = useState(null);
  const [lastEvent, setLastEvent] = useState(null);
  const popupRef = useRef(null);
  const pollRef = useRef(null);
  const allowedOriginRef = useRef(STG_ORIGIN);

  // Listen for postMessage events posted by the Transak popup window.
  // The Transak widget calls window.opener.postMessage(...) on every
  // lifecycle event — same payload shape as the SDK would surface.
  useEffect(() => {
    const handler = (event) => {
      if (event.origin !== allowedOriginRef.current) return;
      const data = event.data;
      if (!data || typeof data !== 'object') return;
      // Transak events carry an `event_id` field like "TRANSAK_ORDER_SUCCESSFUL"
      const name = data.event_id || data.eventName || data.type;
      if (!name || typeof name !== 'string' || !name.startsWith('TRANSAK_')) return;

      setLastEvent({ name, at: new Date().toISOString() });
      onEvent?.(name, data);
      transakApi.logEvent(walletAddress, name, data).catch(() => {});
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [walletAddress, onEvent]);

  // Poll for popup close — fires the synthetic TRANSAK_WIDGET_CLOSE
  // event if the user dismisses the popup manually.
  const startCloseWatcher = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => {
      if (!popupRef.current || popupRef.current.closed) {
        clearInterval(pollRef.current);
        pollRef.current = null;
        if (popupRef.current) {
          const name = 'TRANSAK_WIDGET_CLOSE';
          setLastEvent({ name, at: new Date().toISOString() });
          onEvent?.(name, { reason: 'popup_closed' });
          transakApi
            .logEvent(walletAddress, name, { reason: 'popup_closed' })
            .catch(() => {});
        }
        popupRef.current = null;
        setOpening(null);
      }
    }, 600);
  }, [walletAddress, onEvent]);

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (popupRef.current && !popupRef.current.closed) {
      try { popupRef.current.close(); } catch (_) {}
    }
  }, []);

  const launch = useCallback(
    (mode) => {
      if (!walletAddress) return;
      setOpening(mode);

      const widgetUrl = buildWidgetUrl(config, walletAddress, PRODUCT_MAP[mode]);
      allowedOriginRef.current =
        config.environment === 'PRODUCTION' ? PROD_ORIGIN : STG_ORIGIN;

      // Re-focus existing popup if still open
      if (popupRef.current && !popupRef.current.closed) {
        try {
          popupRef.current.location.replace(widgetUrl);
          popupRef.current.focus();
          return;
        } catch (_) {
          try { popupRef.current.close(); } catch (_) {}
        }
      }

      const popup = window.open(widgetUrl, 'transak-widget', POPUP_FEATURES);
      if (!popup) {
        // Browser blocked the popup — fall back to a same-tab navigation
        window.location.href = widgetUrl;
        return;
      }
      popupRef.current = popup;
      try { popup.focus(); } catch (_) {}
      startCloseWatcher();

      // Synthetic "launcher pressed" — useful for audit before Transak
      // sends its own TRANSAK_WIDGET_INITIALISED
      const name = 'TRANSAK_WIDGET_LAUNCHED';
      setLastEvent({ name, at: new Date().toISOString() });
      onEvent?.(name, { mode });
      transakApi.logEvent(walletAddress, name, { mode }).catch(() => {});
    },
    [config, walletAddress, onEvent, startCloseWatcher]
  );

  const disabled = !walletAddress || !isBSC;
  const cryptoLabel = config?.supports_neno
    ? 'NENO'
    : `${config?.fallback_token || 'USDC'} (NENO listing pending on Transak staging)`;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6" data-testid="transak-launcher">
      <div className="flex items-baseline justify-between mb-1">
        <h2 className="text-white text-lg font-semibold">Step 2 — Trade through Transak</h2>
        <span className="text-xs text-purple-300 uppercase tracking-wider">{config?.environment}</span>
      </div>
      <p className="text-gray-300 text-sm mb-3">
        Pair: <span className="font-mono text-purple-200">{cryptoLabel}</span> on{' '}
        <span className="font-mono text-purple-200">{(config?.network || 'bsc').toUpperCase()}</span>{' '}
        — fiat: <span className="font-mono text-purple-200">{config?.fiat_currency || 'EUR'}</span>
      </p>
      <div className="flex items-start gap-2 text-xs text-gray-400 mb-5">
        <ExternalLink className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-purple-300" />
        <p>
          Transak opens in a separate popup window — never an iframe inside this page. This
          honours Transak's <code>frame-ancestors</code> policy <em>and</em> makes the
          non-custodial boundary visually unambiguous: their KYC + payment rails run in their
          own browser context, not embedded in ours. walletAddress is locked to the address you
          connected above (<code>disableWalletAddressForm=true</code>).
        </p>
      </div>

      <div className="grid sm:grid-cols-3 gap-3">
        <LaunchButton
          label="Buy Crypto"
          icon={<ArrowUpRight className="h-4 w-4" />}
          color="bg-emerald-600 hover:bg-emerald-700"
          loading={opening === 'BUY'}
          disabled={disabled}
          onClick={() => launch('BUY')}
          testId="launch-buy-btn"
        />
        <LaunchButton
          label="Sell Crypto"
          icon={<ArrowDownRight className="h-4 w-4" />}
          color="bg-rose-600 hover:bg-rose-700"
          loading={opening === 'SELL'}
          disabled={disabled}
          onClick={() => launch('SELL')}
          testId="launch-sell-btn"
        />
        <LaunchButton
          label="Swap (Buy/Sell)"
          icon={<RefreshCw className="h-4 w-4" />}
          color="bg-purple-600 hover:bg-purple-700"
          loading={opening === 'SWAP'}
          disabled={disabled}
          onClick={() => launch('SWAP')}
          testId="launch-swap-btn"
        />
      </div>

      {disabled && (
        <p className="text-yellow-300 text-xs mt-4" data-testid="launcher-disabled-note">
          {walletAddress
            ? 'Switch your wallet to BNB Smart Chain to enable Buy/Sell/Swap.'
            : 'Connect your wallet first to enable Buy/Sell/Swap.'}
        </p>
      )}

      {lastEvent && (
        <div
          className="mt-5 rounded-lg border border-white/5 bg-black/20 px-3 py-2 text-xs text-gray-300"
          data-testid="last-event"
        >
          Last Transak event:{' '}
          <span className="font-mono text-purple-200">{lastEvent.name}</span>{' '}
          <span className="text-gray-500">@ {new Date(lastEvent.at).toLocaleTimeString()}</span>
        </div>
      )}
    </div>
  );
};

const LaunchButton = ({ label, icon, color, loading, disabled, onClick, testId }) => (
  <button
    onClick={onClick}
    disabled={disabled || loading}
    className={`${color} disabled:opacity-40 text-white px-4 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all`}
    data-testid={testId}
  >
    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
    <span>{loading ? 'Opening…' : label}</span>
  </button>
);
