import React, { useEffect, useState } from 'react';
import {
  Header,
  DisclaimerBar,
  Footer,
  StatusBanner,
  MarketTickerRibbon,
  type DataMode,
} from './features/shell';
import { CardTab } from './features/card/CardTab';
import { StockTab } from './features/stock';
import { CompareTab } from './features/compare';
import { ScenarioTab } from './features/scenario';
import { HealthTab } from './features/health';
import { SourcesTab } from './features/sources';
import { SAMPLE_CARD } from './features/card/sample';
import { useChatStore } from './state/chat';
import { cn } from './lib/utils';
import {
  Activity,
  Sliders,
  HeartPulse,
  Newspaper,
  Search,
  Layers,
  X,
} from 'lucide-react';
import { ChatPanel } from './features/chat/ChatPanel';
import type { ViewLinkData } from './api/sse';

export type TabKey = 'stock' | 'card' | 'scenario' | 'compare' | 'sources' | 'health';

export default function App(): React.JSX.Element {
  const [activeTab, setActiveTab] = useState<TabKey>('stock');
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<number | null>(null);
  const [compareCodes, setCompareCodes] = useState<string[]>(['1155A1', '1155B1']);
  const [currentTicker, setCurrentTicker] = useState<string>('MAYBANK');
  const [meta, setMeta] = useState<{
    mode: DataMode;
    as_of?: string;
    market_open?: boolean;
    stale?: boolean;
    chat_enabled?: boolean;
  }>({
    mode: 'sample',
    as_of: '2026-10-16 16:30',
    market_open: false,
    stale: false,
    chat_enabled: false,
  });

  const activeCard = useChatStore((state) => state.activeCard);
  const setActiveCard = useChatStore((state) => state.setActiveCard);
  const cardToDisplay = activeCard || SAMPLE_CARD;

  const fetchAndSetCard = async (code: string, days?: number) => {
    try {
      const url = days ? `/api/warrants/${code}?holding_days=${days}` : `/api/warrants/${code}`;
      const resp = await fetch(url);
      if (resp.ok) {
        const card = await resp.json();
        setActiveCard(card);
        return card;
      }
    } catch {
      // fallback
    }
    return null;
  };

  const handleHoldingDaysChange = async (days: number) => {
    if (cardToDisplay.code) {
      await fetchAndSetCard(cardToDisplay.code, days);
    }
  };

  const handleInspectWarrant = async (code: string) => {
    await fetchAndSetCard(code);
    setActiveTab('card');
  };

  const handleSimulateWarrant = async (code: string) => {
    await fetchAndSetCard(code);
    setActiveTab('scenario');
  };

  const handleCompareWarrants = (codes: string[]) => {
    setCompareCodes(codes);
    setActiveTab('compare');
  };

  const handleAddToCompare = (code: string) => {
    if (!compareCodes.includes(code)) {
      setCompareCodes((prev) => [...prev, code].slice(-4));
    }
    setActiveTab('compare');
  };

  const [chatOpen, setChatOpen] = useState(false);

  const handleLinkClick = async (href: string, link: ViewLinkData) => {
    try {
      const url = new URL(href, window.location.origin);
      const tabParam = url.searchParams.get('tab') as TabKey | null;
      const targetTab: TabKey =
        tabParam && ['stock', 'card', 'scenario', 'compare', 'sources', 'health'].includes(tabParam)
          ? tabParam
          : (link.kind === 'card' ||
             link.kind === 'scenario' ||
             link.kind === 'compare' ||
             link.kind === 'sources' ||
             link.kind === 'stock' ||
             link.kind === 'health'
              ? (link.kind as TabKey)
              : 'stock');

      if (link.entity?.code) {
        await fetchAndSetCard(link.entity.code);
      }
      if (link.entity?.codes && link.entity.codes.length > 0) {
        setCompareCodes(link.entity.codes);
      }
      if (link.entity?.ticker) {
        setCurrentTicker(link.entity.ticker);
      }

      setActiveTab(targetTab);
      window.history.pushState(null, '', href);
    } catch {
      // fallback
    }
  };

  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get('tab') as TabKey | null;
      const targetTab: TabKey =
        tabParam && ['stock', 'card', 'scenario', 'compare', 'sources', 'health'].includes(tabParam)
          ? tabParam
          : 'stock';

      const codeParam = params.get('code');
      if (codeParam) {
        fetchAndSetCard(codeParam);
      }
      const codesParam = params.get('codes');
      if (codesParam) {
        const splitCodes = codesParam.split(',').filter(Boolean);
        if (splitCodes.length >= 2) {
          setCompareCodes(splitCodes);
        }
      }
      const tickerParam = params.get('ticker');
      if (tickerParam) {
        setCurrentTicker(tickerParam);
      }

      setActiveTab(targetTab);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      try {
        const params = new URLSearchParams(window.location.search);
        const tabParam = params.get('tab') as TabKey | null;
        if (tabParam && ['stock', 'card', 'scenario', 'compare', 'sources', 'health'].includes(tabParam)) {
          setActiveTab(tabParam);
        }
        const codeParam = params.get('code');
        if (codeParam) {
          fetchAndSetCard(codeParam);
        }
        const codesParam = params.get('codes');
        if (codesParam) {
          const splitCodes = codesParam.split(',').filter(Boolean);
          if (splitCodes.length >= 2) {
            setCompareCodes(splitCodes);
          }
        }
        const tickerParam = params.get('ticker');
        if (tickerParam) {
          setCurrentTicker(tickerParam);
        }
      } catch {
        // ignore
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    try {
      const params = new URLSearchParams();
      params.set('tab', activeTab);
      if (activeCard?.code && (activeTab === 'card' || activeTab === 'scenario' || activeTab === 'sources')) {
        params.set('code', activeCard.code);
      }
      if (activeTab === 'card' && activeCard?.holding_days) {
        params.set('days', String(activeCard.holding_days));
      }
      if (activeTab === 'compare' && compareCodes.length > 0) {
        params.set('codes', compareCodes.join(','));
      }
      if ((activeTab === 'stock' || activeTab === 'sources') && currentTicker) {
        params.set('ticker', currentTicker);
      }
      const newSearch = `?${params.toString()}`;
      if (window.location.search !== newSearch) {
        window.history.replaceState(null, '', newSearch);
      }
    } catch {
      // ignore
    }
  }, [activeTab, activeCard?.code, activeCard?.holding_days, compareCodes, currentTicker]);

  useEffect(() => {
    let mounted = true;
    const fetchMeta = async () => {
      try {
        const resp = await fetch('/api/meta');
        if (resp.ok) {
          const data = await resp.json();
          if (mounted) {
            setMeta({
              mode: (data.mode as DataMode) || 'sample',
              as_of: data.as_of
                ? new Date(data.as_of).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : undefined,
              market_open: Boolean(data.market_open),
              stale: Boolean(data.stale),
              chat_enabled: Boolean(data.chat_enabled),
            });
          }
        }
      } catch {
        // Fallback gracefully if backend is offline
      }
    };

    fetchMeta();
    const timer = setInterval(fetchMeta, 30000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  const isCall = cardToDisplay.type?.toLowerCase() === 'call';
  const daysLeft = cardToDisplay.metrics.days_to_expiry ?? 0;

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground antialiased selection:bg-primary/20">
      <DisclaimerBar />
      <Header
        mode={meta.mode}
        asOf={meta.as_of}
        isStale={meta.stale}
        marketOpen={meta.market_open}
        selectedSnapshotId={selectedSnapshotId}
        onSelectSnapshot={setSelectedSnapshotId}
        chatEnabled={meta.chat_enabled}
        chatOpen={chatOpen}
        onToggleChat={() => setChatOpen((prev) => !prev)}
      />

      {meta.stale && (
        <StatusBanner
          type="warning"
          message="Market data is currently stale (>20 minutes old) during active Bursa trading hours. Prices may lag real exchange quotes."
        />
      )}

      {meta.mode === 'degraded' && (
        <StatusBanner
          type="error"
          message="Primary data feeds are degraded. Operating on fallback snapshot data."
        />
      )}

      <main className="flex-1 p-3 sm:p-5 lg:p-6 max-w-[1720px] mx-auto w-full space-y-4">
        {/* Dynamic Bursa Market Ribbon */}
        <MarketTickerRibbon
          activeTicker={currentTicker}
          onSelectTicker={(t) => {
            setCurrentTicker(t);
            setActiveTab('stock');
          }}
        />

        {/* Active Warrant Context Banner */}
        <div className="rounded-xl border border-border/80 bg-card/95 backdrop-blur-md px-4 py-3 shadow-xs">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            {/* Left: Active Warrant Metadata */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-md bg-primary/10 border border-primary/25 px-2 py-0.5 text-[10px] font-bold text-primary uppercase tracking-wider">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                  Active Warrant
                </span>
                <span className="font-mono text-base font-extrabold text-foreground">
                  {cardToDisplay.code}
                </span>
                <span
                  className={cn(
                    'text-[10px] font-extrabold px-2 py-0.5 rounded-md border uppercase font-mono',
                    isCall
                      ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
                      : 'bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/30'
                  )}
                >
                  {cardToDisplay.type}
                </span>
                <span className="text-xs font-semibold text-muted-foreground bg-muted/60 px-2 py-0.5 rounded-md border border-border">
                  {cardToDisplay.underlying_ticker}
                </span>
              </div>

              <div className="h-4 w-px bg-border hidden sm:block" />

              {/* Quick Metrics Chips */}
              <div className="flex flex-wrap items-center gap-3 sm:gap-4 text-xs font-mono">
                <div>
                  <span className="text-muted-foreground text-[10px] uppercase font-sans block">Spot</span>
                  <span className="font-semibold text-foreground">
                    {cardToDisplay.display_underlying_price || '—'}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground text-[10px] uppercase font-sans block">Strike</span>
                  <span className="font-semibold text-foreground">
                    {cardToDisplay.display_strike}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground text-[10px] uppercase font-sans block">Bid / Ask</span>
                  <span className="font-semibold text-foreground">
                    {cardToDisplay.display_bid || '—'} / {cardToDisplay.display_ask || '—'}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground text-[10px] uppercase font-sans block">Eff. Gearing</span>
                  <span className="font-bold text-indigo-600 dark:text-indigo-400">
                    {cardToDisplay.metrics.display_effective_gearing || '—'}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground text-[10px] uppercase font-sans block">Spread</span>
                  <span className="font-semibold text-foreground">
                    {cardToDisplay.metrics.display_spread_pct || '—'}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground text-[10px] uppercase font-sans block">Expiry</span>
                  <span className="font-semibold text-foreground">
                    {cardToDisplay.expiry_date} ({cardToDisplay.metrics.display_days_to_expiry || `${daysLeft}d`})
                  </span>
                </div>
              </div>
            </div>

            {/* Right: Quick Action Buttons */}
            <div className="flex items-center gap-2 self-end lg:self-center shrink-0">
              <button
                type="button"
                onClick={() => setActiveTab('card')}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all shadow-2xs border',
                  activeTab === 'card'
                    ? 'bg-indigo-600 text-white border-indigo-700'
                    : 'bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border-indigo-200/60 dark:border-indigo-800/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/60'
                )}
              >
                <Activity className="h-3.5 w-3.5" />
                <span>X-Ray Card</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('scenario')}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all shadow-2xs border',
                  activeTab === 'scenario'
                    ? 'bg-emerald-600 text-white border-emerald-700'
                    : 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200/60 dark:border-emerald-800/40 hover:bg-emerald-100 dark:hover:bg-emerald-900/60'
                )}
              >
                <Sliders className="h-3.5 w-3.5" />
                <span>Simulate</span>
              </button>

              <button
                type="button"
                onClick={() => handleAddToCompare(cardToDisplay.code)}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all shadow-2xs border',
                  activeTab === 'compare'
                    ? 'bg-purple-600 text-white border-purple-700'
                    : 'bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border-purple-200/60 dark:border-purple-800/40 hover:bg-purple-100 dark:hover:bg-purple-900/60'
                )}
              >
                <Layers className="h-3.5 w-3.5" />
                <span>Compare</span>
              </button>
            </div>
          </div>
        </div>

        {/* Primary Terminal Navigation Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between border-b-2 border-border pb-2.5 gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('stock')}
              className={cn(
                'inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-all shadow-2xs',
                activeTab === 'stock'
                  ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-xs'
                  : 'border border-border bg-card hover:bg-muted text-foreground'
              )}
            >
              <Search className="h-3.5 w-3.5" />
              <span>Stock Screener</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('card')}
              className={cn(
                'inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-all shadow-2xs',
                activeTab === 'card'
                  ? 'bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-xs'
                  : 'border border-border bg-card hover:bg-muted text-foreground'
              )}
            >
              <Activity className="h-3.5 w-3.5" />
              <span>Warrant X-Ray</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('scenario')}
              className={cn(
                'inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-all shadow-2xs',
                activeTab === 'scenario'
                  ? 'bg-gradient-to-r from-amber-500 to-orange-600 text-white shadow-xs'
                  : 'border border-border bg-card hover:bg-muted text-foreground'
              )}
            >
              <Sliders className="h-3.5 w-3.5" />
              <span>Scenario Simulator</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('compare')}
              className={cn(
                'inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-all shadow-2xs',
                activeTab === 'compare'
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-xs'
                  : 'border border-border bg-card hover:bg-muted text-foreground'
              )}
            >
              <Layers className="h-3.5 w-3.5" />
              <span>Multi-Warrant Compare</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('sources')}
              className={cn(
                'inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-all shadow-2xs',
                activeTab === 'sources'
                  ? 'bg-gradient-to-r from-sky-600 to-cyan-600 text-white shadow-xs'
                  : 'border border-border bg-card hover:bg-muted text-foreground'
              )}
            >
              <Newspaper className="h-3.5 w-3.5" />
              <span>7-Day Market News</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('health')}
              className={cn(
                'inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-all shadow-2xs',
                activeTab === 'health'
                  ? 'bg-gradient-to-r from-rose-600 to-pink-600 text-white shadow-xs'
                  : 'border border-border bg-card hover:bg-muted text-foreground'
              )}
            >
              <HeartPulse className="h-3.5 w-3.5" />
              <span>Data Health</span>
            </button>
          </div>

          {/* Right Status Badge */}
          <div className="flex items-center gap-2 self-end md:self-auto">
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1 text-xs font-mono font-medium text-foreground">
              <span className="text-muted-foreground uppercase text-[10px]">Active Universe:</span>
              <span className="font-bold text-primary">{currentTicker}</span>
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1 text-xs font-mono font-medium text-muted-foreground">
              <span className="text-muted-foreground uppercase text-[10px]">Warrant:</span>
              <span className="font-bold text-foreground">{cardToDisplay.code}</span>
            </span>
          </div>
        </div>

        {/* Tab Content Container */}
        <div className="pt-2">
          {activeTab === 'stock' && (
            <StockTab
              initialTicker={currentTicker}
              onInspectWarrant={handleInspectWarrant}
              onSimulateWarrant={handleSimulateWarrant}
              onCompareWarrants={handleCompareWarrants}
            />
          )}

          {activeTab === 'card' && (
            <CardTab
              card={cardToDisplay}
              onHoldingDaysChange={handleHoldingDaysChange}
              onSimulate={handleSimulateWarrant}
              onCompare={handleAddToCompare}
            />
          )}

          {activeTab === 'scenario' && (
            <ScenarioTab
              warrantCode={cardToDisplay.code}
              maxDays={cardToDisplay.metrics.days_to_expiry ?? 60}
            />
          )}

          {activeTab === 'compare' && (
            <CompareTab
              initialCodes={compareCodes}
              onInspectWarrant={handleInspectWarrant}
            />
          )}

          {activeTab === 'sources' && <SourcesTab />}

          {activeTab === 'health' && <HealthTab />}
        </div>
      </main>

      {meta.chat_enabled && chatOpen && (
        <aside
          aria-label="Risk Copilot Chat Drawer"
          className="fixed inset-y-0 right-0 z-40 w-full sm:w-[460px] bg-card/95 backdrop-blur-md border-l-2 border-border shadow-2xl p-3 sm:p-4 flex flex-col pt-16 sm:pt-4"
        >
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-border/60">
            <span className="text-xs font-bold text-foreground">Risk Copilot Chat</span>
            <button
              type="button"
              onClick={() => setChatOpen(false)}
              className="text-xs text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-muted transition-colors"
              title="Close Chat"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <ChatPanel onLinkClick={handleLinkClick} className="flex-1 min-h-0" />
        </aside>
      )}

      <Footer />
    </div>
  );
}
