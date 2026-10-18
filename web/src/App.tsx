import React, { useEffect, useState } from 'react';
import {
  Header,
  DisclaimerBar,
  Footer,
  StatusBanner,
  MarketTickerRibbon,
  type DataMode,
} from './features/shell';
import { ChatPanel } from './features/chat';
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
} from 'lucide-react';

export default function App(): React.JSX.Element {
  const [activeTab, setActiveTab] = useState<
    'card' | 'stock' | 'compare' | 'scenario' | 'sources' | 'health'
  >('card');
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<number | null>(null);
  const [compareCodes, setCompareCodes] = useState<string[]>(['1155A1', '1155B1']);
  const [currentTicker, setCurrentTicker] = useState<string>('MAYBANK');
  const [meta, setMeta] = useState<{
    mode: DataMode;
    as_of?: string;
    market_open?: boolean;
    stale?: boolean;
  }>({
    mode: 'sample',
    as_of: '2026-10-16 16:30',
    market_open: false,
    stale: false,
  });

  const activeCard = useChatStore((state) => state.activeCard);
  const setActiveCard = useChatStore((state) => state.setActiveCard);
  const cardToDisplay = activeCard || SAMPLE_CARD;

  const handleInspectWarrant = async (code: string) => {
    try {
      const resp = await fetch(`/api/warrants/${code}`);
      if (resp.ok) {
        const card = await resp.json();
        setActiveCard(card);
      }
    } catch {
      // fallback
    }
    setActiveTab('card');
  };

  const handleCompareWarrants = (codes: string[]) => {
    setCompareCodes(codes);
    setActiveTab('compare');
  };

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
              as_of: data.as_of ? new Date(data.as_of).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : undefined,
              market_open: Boolean(data.market_open),
              stale: Boolean(data.stale),
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

      <main className="flex-1 p-3 sm:p-5 lg:p-6 max-w-[1680px] mx-auto w-full space-y-4">
        {/* Dynamic Bursa Market Ribbon */}
        <MarketTickerRibbon
          activeTicker={currentTicker}
          onSelectTicker={(t) => {
            setCurrentTicker(t);
            setActiveTab('stock');
          }}
        />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Chat Copilot Column */}
          <section className="lg:col-span-5 xl:col-span-4 h-[calc(100vh-230px)] min-h-[580px] sticky top-20">
            <ChatPanel className="h-full" />
          </section>

          {/* Quant & Evidence Column */}
          <section className="lg:col-span-7 xl:col-span-8 space-y-4">
            <div className="flex flex-wrap items-center justify-between border-b-2 border-border pb-2.5 gap-2">
              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                <button
                  type="button"
                  onClick={() => setActiveTab('card')}
                  className={cn(
                    'inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all',
                    activeTab === 'card'
                      ? 'bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-xs'
                      : 'border border-border bg-card hover:bg-muted text-foreground'
                  )}
                >
                  <Activity className="h-3.5 w-3.5" />
                  <span>Warrant Card</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('stock')}
                  className={cn(
                    'inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all',
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
                  onClick={() => setActiveTab('compare')}
                  className={cn(
                    'inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all',
                    activeTab === 'compare'
                      ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-xs'
                      : 'border border-border bg-card hover:bg-muted text-foreground'
                  )}
                >
                  <Layers className="h-3.5 w-3.5" />
                  <span>Compare</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('scenario')}
                  className={cn(
                    'inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all',
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
                  onClick={() => setActiveTab('sources')}
                  className={cn(
                    'inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all',
                    activeTab === 'sources'
                      ? 'bg-gradient-to-r from-sky-600 to-cyan-600 text-white shadow-xs'
                      : 'border border-border bg-card hover:bg-muted text-foreground'
                  )}
                >
                  <Newspaper className="h-3.5 w-3.5" />
                  <span>Cited Sources</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('health')}
                  className={cn(
                    'inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all',
                    activeTab === 'health'
                      ? 'bg-gradient-to-r from-rose-600 to-pink-600 text-white shadow-xs'
                      : 'border border-border bg-card hover:bg-muted text-foreground'
                  )}
                >
                  <HeartPulse className="h-3.5 w-3.5" />
                  <span>Data Health</span>
                </button>
              </div>

              <div className="text-[11px] font-mono font-bold text-foreground">
                {activeTab === 'health'
                  ? 'System Status'
                  : activeTab === 'sources'
                  ? '7-Day Grounded News'
                  : activeTab === 'stock'
                  ? `Universe: ${currentTicker}`
                  : activeTab === 'compare'
                  ? `Comparing ${compareCodes.length} Warrants`
                  : activeCard
                  ? `Pinned: ${cardToDisplay.code}`
                  : 'Preview: MAYBANK-C28'}
              </div>
            </div>

            {activeTab === 'card' && <CardTab card={cardToDisplay} />}
            {activeTab === 'stock' && (
              <StockTab
                initialTicker={currentTicker}
                onInspectWarrant={handleInspectWarrant}
                onCompareWarrants={handleCompareWarrants}
              />
            )}
            {activeTab === 'compare' && (
              <CompareTab
                initialCodes={compareCodes}
                onInspectWarrant={handleInspectWarrant}
              />
            )}
            {activeTab === 'scenario' && (
              <ScenarioTab
                warrantCode={cardToDisplay.code}
                maxDays={cardToDisplay.metrics.days_to_expiry ?? 60}
              />
            )}
            {activeTab === 'sources' && <SourcesTab />}
            {activeTab === 'health' && <HealthTab />}
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}
