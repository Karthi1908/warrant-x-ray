import React, { useState, useEffect } from 'react';
import type { StockSummary, WarrantListItem, WarrantSearchResponse } from './types';
import { StockOverviewBar } from './StockOverviewBar';
import { NearestWarrantsList } from './NearestWarrantsList';
import { WarrantTable, type SortField } from './WarrantTable';
import { cn } from '../../lib/utils';
import {
  Search,
  Layers,
  ArrowRight,
  RefreshCw,
  X,
} from 'lucide-react';

export interface StockTabProps {
  initialTicker?: string;
  onInspectWarrant?: (code: string) => void;
  onSimulateWarrant?: (code: string) => void;
  onCompareWarrants?: (codes: string[]) => void;
  className?: string;
}

const POPULAR_TICKERS = [
  'MAYBANK',
  'TENAGA',
  'PBBANK',
  'CIMB',
  'IHH',
  'CELCOMDIGI',
  'PCHEM',
  'INARI',
  'YTL',
  'YTLPOWR',
  'GAMUDA',
  'SUNWAY',
];

interface UnderlyingOption {
  ticker: string;
  code?: string;
  name?: string;
  total_warrants?: number;
}

export const StockTab: React.FC<StockTabProps> = ({
  initialTicker = 'MAYBANK',
  onInspectWarrant,
  onSimulateWarrant,
  onCompareWarrants,
  className,
}) => {
  const [ticker, setTicker] = useState(initialTicker);
  const [searchInput, setSearchInput] = useState(initialTicker);
  const [allUnderlyings, setAllUnderlyings] = useState<UnderlyingOption[]>([]);
  const [typeFilter, setTypeFilter] = useState<'all' | 'call' | 'put'>('all');
  const [selectedIssuer, setSelectedIssuer] = useState<string>('all');
  const [moneynessFilter, setMoneynessFilter] = useState<'all' | 'itm' | 'atm' | 'otm'>('all');
  const [ivBasis, setIvBasis] = useState<string>('mid');
  const [sortField, setSortField] = useState<SortField>('strike');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  const [summary, setSummary] = useState<StockSummary | null>(null);
  const [warrants, setWarrants] = useState<WarrantListItem[]>([]);
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load all 50+ underlyings for selector dropdown
  useEffect(() => {
    let mounted = true;
    const fetchUnderlyings = async () => {
      try {
        const resp = await fetch('/api/underlyings');
        if (resp.ok) {
          const data = await resp.json();
          if (mounted && Array.isArray(data.underlyings)) {
            setAllUnderlyings(data.underlyings);
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

  // Sync external ticker changes (e.g. from MarketTickerRibbon)
  useEffect(() => {
    if (initialTicker && initialTicker !== ticker) {
      setTicker(initialTicker);
      setSearchInput(initialTicker);
      setSelectedCodes([]);
    }
  }, [initialTicker]);

  // Fetch stock summary
  useEffect(() => {
    let mounted = true;
    const fetchSummary = async () => {
      try {
        const resp = await fetch(`/api/stock/${ticker}`);
        if (resp.ok) {
          const data: StockSummary = await resp.json();
          if (mounted) {
            setSummary(data);
          }
        }
      } catch (err) {
        // Fallback gracefully
      }
    };

    fetchSummary();
    return () => {
      mounted = false;
    };
  }, [ticker]);

  // Fetch warrants list
  useEffect(() => {
    let mounted = true;
    const fetchWarrants = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        params.set('underlying', ticker);
        if (typeFilter !== 'all') params.set('type', typeFilter);
        if (selectedIssuer !== 'all') params.set('issuer', selectedIssuer);
        if (moneynessFilter !== 'all') params.set('moneyness', moneynessFilter);
        params.set('iv_basis', ivBasis);
        params.set('sort_by', sortField);
        params.set('order', sortOrder);
        params.set('limit', '50');

        const resp = await fetch(`/api/warrants?${params.toString()}`);
        if (resp.ok) {
          const data: WarrantSearchResponse = await resp.json();
          if (mounted) {
            setWarrants(data.results || []);
          }
        } else {
          if (mounted) {
            setError(`Failed to load warrants: HTTP ${resp.status}`);
          }
        }
      } catch (err) {
        if (mounted) {
          setError('Error loading warrants list.');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchWarrants();
    return () => {
      mounted = false;
    };
  }, [ticker, typeFilter, selectedIssuer, moneynessFilter, ivBasis, sortField, sortOrder]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = searchInput.trim().toUpperCase();
    if (clean) {
      setTicker(clean);
      setSelectedCodes([]);
    }
  };

  const handleTickerSelect = (t: string) => {
    setTicker(t);
    setSearchInput(t);
    setSelectedCodes([]);
  };

  const handleToggleSelect = (code: string) => {
    setSelectedCodes((prev) => {
      if (prev.includes(code)) {
        return prev.filter((c) => c !== code);
      }
      if (prev.length >= 3) {
        return prev;
      }
      return [...prev, code];
    });
  };

  const handleSortChange = (field: SortField) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Ticker Selector Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 bg-card p-4 shadow-xs">
        <div className="flex flex-wrap items-center gap-2 flex-1 max-w-xl">
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 min-w-[200px]">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search Ticker (e.g. PBBANK, GAMUDA)"
                className="w-full rounded-lg border border-border bg-background py-1.5 pl-8 pr-3 text-xs font-mono font-medium text-foreground placeholder:text-muted-foreground focus:outline-hidden focus:ring-1 focus:ring-primary"
              />
            </div>
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-all shadow-xs"
            >
              Find
            </button>
          </form>

          {allUnderlyings.length > 0 && (
            <select
              value={ticker}
              aria-label="Select Underlying Company"
              onChange={(e) => handleTickerSelect(e.target.value)}
              className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-mono font-semibold text-foreground focus:outline-hidden focus:ring-1 focus:ring-primary shadow-2xs"
            >
              <option value="" disabled>Choose from {allUnderlyings.length} Companies...</option>
              {allUnderlyings.map((u) => (
                <option key={u.ticker} value={u.ticker}>
                  {u.ticker} - {u.name || u.ticker} ({u.total_warrants || 10} warrants)
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Quick Tickers */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-[11px] text-muted-foreground mr-1">Popular:</span>
          {POPULAR_TICKERS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => handleTickerSelect(t)}
              className={cn(
                'rounded-md px-2 py-1 text-xs font-mono font-medium transition-all',
                ticker === t
                  ? 'bg-primary/15 text-primary border border-primary/30 font-bold'
                  : 'border border-border/50 bg-muted/30 text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Stock Overview Bar */}
      {summary && <StockOverviewBar summary={summary} />}

      {/* 5 Nearest to the money warrants */}
      {summary && summary.nearest_warrants.length > 0 && (
        <NearestWarrantsList
          nearest={summary.nearest_warrants}
          selectedCodes={selectedCodes}
          onToggleSelect={handleToggleSelect}
          onInspect={onInspectWarrant}
        />
      )}

      {/* Dynamic 4-KPI Screener Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-border/80 bg-card p-3 shadow-2xs hover:shadow-xs transition-shadow">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Warrants in View
          </span>
          <div className="text-lg font-bold font-mono text-foreground mt-0.5 flex items-baseline gap-1.5">
            <span>{warrants.length}</span>
            <span className="text-[11px] font-normal text-muted-foreground">total</span>
          </div>
        </div>

        <div className="rounded-xl border border-border/80 bg-card p-3 shadow-2xs hover:shadow-xs transition-shadow">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Call / Put Distribution
          </span>
          <div className="text-xs font-mono font-bold mt-1 flex items-center gap-2">
            <span className="text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              {warrants.filter((w) => w.type?.toLowerCase() === 'call').length} Calls
            </span>
            <span className="text-purple-700 dark:text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
              {warrants.filter((w) => w.type?.toLowerCase() === 'put').length} Puts
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-border/80 bg-card p-3 shadow-2xs hover:shadow-xs transition-shadow">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Avg Effective Gearing
          </span>
          <div className="text-lg font-bold font-mono text-indigo-600 dark:text-indigo-400 mt-0.5">
            {warrants.filter((w) => typeof w.effective_gearing === 'number' && w.effective_gearing > 0).length > 0
              ? `${(
                  warrants
                    .filter((w) => typeof w.effective_gearing === 'number' && w.effective_gearing > 0)
                    .reduce((sum, w) => sum + (w.effective_gearing || 0), 0) /
                  warrants.filter((w) => typeof w.effective_gearing === 'number' && w.effective_gearing > 0).length
                ).toFixed(1)}x`
              : '—'}
          </div>
        </div>

        <div className="rounded-xl border border-border/80 bg-card p-3 shadow-2xs hover:shadow-xs transition-shadow">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Tightest Spread Pick
          </span>
          <div className="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400 mt-1 flex items-center gap-1.5">
            {(() => {
              const best = warrants.reduce<WarrantListItem | null>((acc, w) => {
                if (typeof w.spread_pct !== 'number' || w.spread_pct <= 0) return acc;
                if (!acc || (acc.spread_pct ?? 1) > w.spread_pct) return w;
                return acc;
              }, null);
              return best ? (
                <span>
                  <strong className="text-foreground">{best.code}</strong> ({best.display_spread_pct})
                </span>
              ) : (
                <span className="text-muted-foreground">—</span>
              );
            })()}
          </div>
        </div>
      </div>

      {/* Filter and Control Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/60 bg-muted/20 p-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          {/* Type Filter */}
          <div className="flex rounded-lg border border-border bg-card p-0.5">
            {(['all', 'call', 'put'] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTypeFilter(t)}
                className={cn(
                  'rounded-md px-2.5 py-1 text-xs font-semibold uppercase tracking-wider transition-all',
                  typeFilter === t
                    ? 'bg-primary text-primary-foreground shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Issuer Dropdown */}
          {summary && summary.issuers.length > 0 && (
            <select
              value={selectedIssuer}
              aria-label="Filter by Issuer"
              onChange={(e) => setSelectedIssuer(e.target.value)}
              className="rounded-lg border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground focus:outline-hidden focus:ring-1 focus:ring-primary"
            >
              <option value="all">All Issuers ({summary.issuer_count})</option>
              {summary.issuers.map((iss) => (
                <option key={iss} value={iss}>
                  {iss}
                </option>
              ))}
            </select>
          )}

          {/* Moneyness Dropdown */}
          <select
            value={moneynessFilter}
            aria-label="Filter by Moneyness"
            onChange={(e) => setMoneynessFilter(e.target.value as any)}
            className="rounded-lg border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground focus:outline-hidden focus:ring-1 focus:ring-primary"
          >
            <option value="all">All Moneyness</option>
            <option value="itm">ITM (In the Money)</option>
            <option value="atm">ATM (At the Money)</option>
            <option value="otm">OTM (Out of the Money)</option>
          </select>
        </div>

        {/* IV Basis Selector */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-muted-foreground">IV Basis:</span>
          <div className="flex rounded-lg border border-border bg-card p-0.5 font-mono text-[11px]">
            {(['mid', 'bid', 'ask', 'last'] as const).map((b) => (
              <button
                key={b}
                type="button"
                onClick={() => setIvBasis(b)}
                className={cn(
                  'rounded px-2 py-0.5 font-bold uppercase transition-all',
                  ivBasis === b
                    ? 'bg-primary text-primary-foreground shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {b}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Floating Compare Action Bar if warrants are selected */}
      {selectedCodes.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/40 bg-primary/10 p-3.5 shadow-sm animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-primary">
              Ready to Compare ({selectedCodes.length}/3):
            </span>
            <div className="flex flex-wrap items-center gap-1.5">
              {selectedCodes.map((code) => (
                <span
                  key={code}
                  className="inline-flex items-center gap-1 rounded-md bg-background/80 border border-primary/30 px-2 py-0.5 text-xs font-mono font-bold text-foreground"
                >
                  <span>{code}</span>
                  <button
                    type="button"
                    onClick={() => handleToggleSelect(code)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          <button
            type="button"
            disabled={selectedCodes.length < 2}
            onClick={() => onCompareWarrants?.(selectedCodes)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all shadow-xs',
              selectedCodes.length >= 2
                ? 'bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer'
                : 'bg-muted text-muted-foreground cursor-not-allowed'
            )}
          >
            <Layers className="h-3.5 w-3.5" />
            <span>
              {selectedCodes.length < 2
                ? 'Select 1 more to compare'
                : `Compare Warrants (${selectedCodes.length})`}
            </span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Warrant Table */}
      {loading ? (
        <div className="flex items-center justify-center p-12 text-muted-foreground text-xs gap-2">
          <RefreshCw className="h-4 w-4 animate-spin text-primary" />
          <span>Loading warrants for {ticker}...</span>
        </div>
      ) : error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-xs text-destructive">
          {error}
        </div>
      ) : (
        <WarrantTable
          warrants={warrants}
          selectedCodes={selectedCodes}
          onToggleSelect={handleToggleSelect}
          onInspect={onInspectWarrant}
          onSimulate={onSimulateWarrant}
          sortField={sortField}
          sortOrder={sortOrder}
          onSortChange={handleSortChange}
          ivBasis={ivBasis}
        />
      )}
    </div>
  );
};
