import React, { useEffect, useState } from 'react';
import {
  Calendar,
  Compass,
  Filter,
  Newspaper,
  RefreshCw,
  Search,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { NewsItemCard, type NewsItemModel } from './NewsItemCard';
import { EvidenceRecord, type EvidencePayload } from './EvidenceRecord';
import { ExternalLinkModal } from './ExternalLinkModal';

const PRESET_TICKERS = [
  'MAYBANK',
  'TENAGA',
  'PBBANK',
  'CIMB',
  'IHH',
  'CELCOMDIGI',
  'PCHEM',
  'INARI',
  'YTL',
  'GAMUDA',
  'SUNWAY',
  'BURSA',
];

export const SourcesTab: React.FC = () => {
  const [selectedTicker, setSelectedTicker] = useState('MAYBANK');
  const [queryInput, setQueryInput] = useState('');
  const [allUnderlyings, setAllUnderlyings] = useState<string[]>([]);
  const [news, setNews] = useState<NewsItemModel[]>([]);
  const [evidence, setEvidence] = useState<EvidencePayload | null>(null);
  const [mode, setMode] = useState('sample');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetchUnderlyings = async () => {
      try {
        const resp = await fetch('/api/underlyings');
        if (resp.ok) {
          const data = await resp.json();
          if (mounted && Array.isArray(data.underlyings)) {
            setAllUnderlyings(data.underlyings.map((u: any) => u.ticker));
          }
        }
      } catch {
        // fallback
      }
    };
    fetchUnderlyings();
    return () => {
      mounted = false;
    };
  }, []);

  // External link modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalUrl, setModalUrl] = useState<string | null>(null);
  const [modalDomain, setModalDomain] = useState<string | undefined>(undefined);

  const fetchNews = async (ticker: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/news?ticker=${encodeURIComponent(ticker)}&max_results=6`);
      if (!resp.ok) {
        throw new Error(`Failed to load news: ${resp.status}`);
      }
      const data = await resp.json();
      setNews(data.news || []);
      setEvidence(data.evidence || null);
      setMode(data.mode || 'sample');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown network error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNews(selectedTicker);
  }, [selectedTicker]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = queryInput.trim().toUpperCase();
    if (clean) {
      setSelectedTicker(clean);
    }
  };

  const handleOpenUrl = (url: string, domain: string) => {
    setModalUrl(url);
    setModalDomain(domain);
    setModalOpen(true);
  };

  return (
    <div className="space-y-4">
      {/* Tab Header Banner */}
      <div className="rounded-xl border border-border/80 bg-card p-4 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20">
              <Newspaper className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-bold text-foreground">Cited News & Source Grounding</h3>
                <span className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-[10px] font-mono uppercase text-muted-foreground">
                  Mode: {mode}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Corroborated Bursa Malaysia disclosures and financial publisher feeds.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center space-x-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-1 text-xs font-semibold">
              <Calendar className="h-3 w-3" />
              <span>Strict 7-Day Window</span>
            </span>
          </div>
        </div>

        {/* Ticker Quick Filters & Search */}
        <div className="mt-4 pt-3 border-t border-border/60 flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="flex items-center space-x-1.5 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
            <span className="text-xs text-muted-foreground mr-1 flex items-center space-x-1">
              <Filter className="h-3 w-3" />
              <span>Top Underlyings:</span>
            </span>
            {PRESET_TICKERS.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => {
                  setSelectedTicker(t);
                  setQueryInput('');
                }}
                className={cn(
                  'px-2.5 py-1 text-xs font-semibold rounded-lg transition-all',
                  selectedTicker === t
                    ? 'bg-primary text-primary-foreground shadow-xs'
                    : 'bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground border border-border/50'
                )}
              >
                {t}
              </button>
            ))}
          </div>

          <form onSubmit={handleSearchSubmit} className="flex items-center space-x-1.5 w-full md:w-auto">
            {allUnderlyings.length > 0 && (
              <select
                value={selectedTicker}
                aria-label="Select company news"
                onChange={(e) => {
                  setSelectedTicker(e.target.value);
                  setQueryInput('');
                }}
                className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-mono font-semibold text-foreground focus:outline-hidden focus:ring-1 focus:ring-primary shadow-2xs"
              >
                <option value="" disabled>All 58 Companies...</option>
                {allUnderlyings.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            )}
            <div className="relative flex-1 md:w-40">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="text"
                placeholder="Ticker (e.g. CIMB)..."
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                className="w-full rounded-lg border border-border bg-background pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-hidden focus:ring-1 focus:ring-primary"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors shrink-0"
            >
              Search
            </button>
            <button
              type="button"
              onClick={() => fetchNews(selectedTicker)}
              disabled={loading}
              className="p-1.5 text-muted-foreground hover:text-foreground rounded-lg border border-border bg-background hover:bg-muted transition-colors shrink-0"
              title="Refresh News"
            >
              <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin text-primary')} />
            </button>
          </form>
        </div>
      </div>

      {/* Error Callout */}
      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-rose-400 text-xs">
          Failed to retrieve news context: {error}
        </div>
      )}

      {/* News Feed Grid */}
      {loading && news.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 rounded-xl border border-dashed border-border bg-card/40 text-muted-foreground space-y-2">
          <RefreshCw className="h-6 w-6 animate-spin text-primary" />
          <p className="text-xs">Fetching and corroborating 7-day news feed for {selectedTicker}...</p>
        </div>
      ) : news.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 rounded-xl border border-dashed border-border bg-card/40 text-muted-foreground space-y-2">
          <Compass className="h-6 w-6 text-muted-foreground/60" />
          <p className="text-xs">No recent news items found within the 7-day window for {selectedTicker}.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {news.map((item, idx) => (
            <NewsItemCard key={`${item.url}-${idx}`} item={item} onOpenUrl={handleOpenUrl} />
          ))}
        </div>
      )}

      {/* Grounding Evidence Envelope Expander */}
      {evidence && <EvidenceRecord evidence={evidence} />}

      {/* External Link Safety Warning Modal */}
      <ExternalLinkModal
        isOpen={modalOpen}
        url={modalUrl}
        domain={modalDomain}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
};
