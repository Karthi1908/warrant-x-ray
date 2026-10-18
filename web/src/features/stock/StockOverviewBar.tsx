import React from 'react';
import type { StockSummary } from './types';
import { cn } from '../../lib/utils';
import {
  Building2,
  Percent,
  Clock,
  ShieldAlert,
  Activity,
} from 'lucide-react';

export interface StockOverviewBarProps {
  summary: StockSummary;
  className?: string;
}

export const StockOverviewBar: React.FC<StockOverviewBarProps> = ({
  summary,
  className,
}) => {
  const totalWarrants = summary.call_count + summary.put_count;

  return (
    <div
      className={cn(
        'rounded-xl border border-border/70 bg-card p-5 shadow-xs space-y-4',
        className
      )}
    >
      {/* Top row: Ticker, Price, Call/Put counters */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/40 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary border border-primary/20 font-mono text-base font-bold">
            {summary.ticker.slice(0, 3)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold tracking-tight text-foreground font-mono">
                {summary.ticker}
              </h2>
              <span className="rounded-md border border-border bg-muted/60 px-2 py-0.5 text-xs font-semibold text-muted-foreground">
                Bursa Malaysia
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              {summary.display_underlying_price ? (
                <span>Underlying: <strong className="text-foreground font-mono">{summary.display_underlying_price}</strong></span>
              ) : (
                <span>Underlying price not available</span>
              )}
            </div>
          </div>
        </div>

        {/* Call vs Put Breakdown */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-muted/30 px-3 py-1.5">
            <span className="text-xs text-muted-foreground">Warrants:</span>
            <span className="text-xs font-bold font-mono text-foreground">{totalWarrants}</span>
            <span className="text-muted-foreground/40">|</span>
            <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 px-1.5 py-0.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 font-mono">
              {summary.call_count} Calls
            </span>
            <span className="inline-flex items-center gap-1 rounded bg-purple-500/10 px-1.5 py-0.5 text-[11px] font-semibold text-purple-600 dark:text-purple-400 font-mono">
              {summary.put_count} Puts
            </span>
          </div>
        </div>
      </div>

      {/* Metrics Row: Median Spread, Median Decay, Realized Vol, Issuers */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-lg border border-border bg-card p-3 shadow-2xs">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-bold mb-1">
            <Percent className="h-3.5 w-3.5 text-amber-600 dark:text-amber-500" />
            <span>Median Spread</span>
          </div>
          <div className="text-base font-bold font-mono text-foreground">
            {summary.display_median_spread_pct ?? 'N/A'}
          </div>
          <div className="text-[10px] text-muted-foreground font-medium">Across active quotes</div>
        </div>

        <div className="rounded-lg border border-border bg-card p-3 shadow-2xs">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-bold mb-1">
            <Clock className="h-3.5 w-3.5 text-rose-600 dark:text-rose-500" />
            <span>Median Decay (5d)</span>
          </div>
          <div className="text-base font-bold font-mono text-foreground">
            {summary.display_median_flat_decay ?? 'N/A'}
          </div>
          <div className="text-[10px] text-muted-foreground font-medium">Flat underlying drift</div>
        </div>

        <div className="rounded-lg border border-border bg-card p-3 shadow-2xs">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-bold mb-1">
            <Activity className="h-3.5 w-3.5 text-blue-600 dark:text-blue-500" />
            <span>Realized Volatility</span>
          </div>
          <div className="text-base font-bold font-mono text-foreground">
            {summary.display_volatility_30d ?? summary.display_volatility_10d ?? 'N/A'}
          </div>
          <div className="text-[10px] text-muted-foreground font-medium">
            {summary.display_volatility_30d ? '30-day annualized' : summary.display_volatility_10d ? '10-day annualized' : 'Price history unavailable'}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card p-3 shadow-2xs">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-bold mb-1">
            <Building2 className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-500" />
            <span>Active Issuers</span>
          </div>
          <div className="text-base font-bold font-mono text-foreground">
            {summary.issuer_count}
          </div>
          <div className="text-[10px] text-muted-foreground font-medium truncate" title={summary.issuers.join(', ')}>
            {summary.issuers.length > 0 ? summary.issuers.slice(0, 3).join(', ') + (summary.issuers.length > 3 ? '...' : '') : 'None'}
          </div>
        </div>
      </div>

      {/* Flag Counts Distribution if any flags are triggered */}
      {Object.keys(summary.flag_counts).length > 0 && (
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border">
          <span className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground">
            <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
            Risk Flags in Universe:
          </span>
          {Object.entries(summary.flag_counts).map(([flagCode, count]) => (
            <span
              key={flagCode}
              className="inline-flex items-center gap-1 rounded-md border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-[11px] font-mono text-amber-600 dark:text-amber-400"
            >
              <span>{flagCode}</span>
              <span className="font-bold">({count})</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
