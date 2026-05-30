import React, { useCallback, useRef, useState } from 'react';
import { Transak } from '@transak/ui-js-sdk';
import { ArrowUpRight, ArrowDownRight, RefreshCw, Loader2 } from 'lucide-react';
import { transakApi } from '../../api/transak';

const STG_WIDGET_BASE = 'https://global-stg.transak.com';
const PROD_WIDGET_BASE = 'https://global.transak.com';

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
  SWAP: 'BUY,SELL', // "Swap" surfaces both tabs in the widget
};

const TRACKED_EVENTS = [
  'TRANSAK_WIDGET_INITIALISED',
  'TRANSAK_WIDGET_OPEN',
  'TRANSAK_ORDER_CREATED',
  'TRANSAK_ORDER_SUCCESSFUL',
  'TRANSAK_ORDER_CANCELLED',
  'TRANSAK_ORDER_FAILED',
  'TRANSAK_WIDGET_CLOSE',
];

export const TransakLauncher = ({ config, walletAddress, isBSC, onEvent }) => {
  const [opening, setOpening] = useState(null); // 'BUY' | 'SELL' | 'SWAP' | null
  const [lastEvent, setLastEvent] = useState(null);
  const activeRef = useRef(null);

  const launch = useCallback(
    (mode) => {
      if (!walletAddress) return;
      if (activeRef.current) {
        // Tear down any previous instance before opening a new one
        try {
          activeRef.current.close();
        } catch (_) {}
        activeRef.current = null;
      }
      setOpening(mode);

      const widgetUrl = buildWidgetUrl(config, walletAddress, PRODUCT_MAP[mode]);
      const transak = new Transak({ widgetUrl });

      TRACKED_EVENTS.forEach((eventName) => {
        Transak.on(eventName, (data) => {
          setLastEvent({ name: eventName, at: new Date().toISOString() });
          onEvent?.(eventName, data);
          // Best-effort backend logging — never blocks the UX
          transakApi
            .logEvent(walletAddress, eventName, data || {})
            .catch(() => {});
          if (eventName === 'TRANSAK_WIDGET_CLOSE') {
            try {
              transak.close();
            } catch (_) {}
            activeRef.current = null;
            setOpening(null);
          }
        });
      });

      activeRef.current = transak;
      transak.init();
    },
    [config, walletAddress, onEvent]
  );

  const disabled = !walletAddress || !isBSC;
  const cryptoLabel = config?.supports_neno ? 'NENO' : `${config?.fallback_token || 'USDC'} (NENO listing pending on Transak staging)`;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6" data-testid="transak-launcher">
      <div className="flex items-baseline justify-between mb-1">
        <h2 className="text-white text-lg font-semibold">Step 2 — Trade through Transak</h2>
        <span className="text-xs text-purple-300 uppercase tracking-wider">{config?.environment}</span>
      </div>
      <p className="text-gray-300 text-sm mb-4">
        Pair: <span className="font-mono text-purple-200">{cryptoLabel}</span> on{' '}
        <span className="font-mono text-purple-200">{(config?.network || 'bsc').toUpperCase()}</span>{' '}
        — fiat: <span className="font-mono text-purple-200">{config?.fiat_currency || 'EUR'}</span>
      </p>
      <p className="text-gray-400 text-xs mb-5">
        walletAddress is locked to the address you connected above (<code>disableWalletAddressForm=true</code>).
      </p>

      <div className="grid sm:grid-cols-3 gap-3">
        <LaunchButton
          label="Buy Crypto"
          mode="BUY"
          icon={<ArrowUpRight className="h-4 w-4" />}
          color="bg-emerald-600 hover:bg-emerald-700"
          loading={opening === 'BUY'}
          disabled={disabled}
          onClick={() => launch('BUY')}
          testId="launch-buy-btn"
        />
        <LaunchButton
          label="Sell Crypto"
          mode="SELL"
          icon={<ArrowDownRight className="h-4 w-4" />}
          color="bg-rose-600 hover:bg-rose-700"
          loading={opening === 'SELL'}
          disabled={disabled}
          onClick={() => launch('SELL')}
          testId="launch-sell-btn"
        />
        <LaunchButton
          label="Swap (Buy/Sell)"
          mode="SWAP"
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
