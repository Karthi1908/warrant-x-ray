import React from 'react';
import type { ComparedWarrantItem } from './types';
import { cn } from '../../lib/utils';
import { ShieldAlert, ExternalLink, X } from 'lucide-react';

export interface CompareGridProps {
  warrants: ComparedWarrantItem[];
  holdingDays: number;
  onRemoveWarrant?: (code: string) => void;
  onInspectWarrant?: (code: string) => void;
  className?: string;
}

interface AttributeRow {
  group: string;
  label: string;
  sublabel?: string;
  getValue: (item: ComparedWarrantItem) => React.ReactNode;
}

export const CompareGrid: React.FC<CompareGridProps> = ({
  warrants,
  holdingDays,
  onRemoveWarrant,
  onInspectWarrant,
  className,
}) => {
  if (warrants.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/80 bg-muted/20 p-12 text-center text-xs text-muted-foreground">
        Select 2 to 3 warrants of the same stock to view side-by-side objective comparison.
      </div>
    );
  }

  const rows: AttributeRow[] = [
    // Identification
    {
      group: 'Identification & Contract',
      label: 'Issuer',
      sublabel: 'Financial institution issuing the warrant & providing market quotes',
      getValue: (w) => <span className="font-sans font-medium text-foreground">{w.issuer}</span>,
    },
    {
      group: 'Identification & Contract',
      label: 'Type',
      sublabel: 'Call (bullish: gains as stock rises) or Put (bearish: gains as stock falls)',
      getValue: (w) => (
        <span
          className={cn(
            'inline-flex rounded px-2 py-0.5 text-[11px] font-bold font-mono uppercase',
            w.type.toLowerCase() === 'call'
              ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
              : 'bg-purple-500/15 text-purple-600 dark:text-purple-400'
          )}
        >
          {w.type}
        </span>
      ),
    },
    {
      group: 'Identification & Contract',
      label: 'Strike Price',
      sublabel: 'Target exercise price the stock must exceed (for Calls) to finish in the money',
      getValue: (w) => <span className="font-mono font-medium text-foreground">{w.display_strike}</span>,
    },
    {
      group: 'Identification & Contract',
      label: 'Exercise Ratio',
      sublabel: 'Number of warrants per 1 underlying share (lower = higher per-warrant exposure)',
      getValue: (w) => <span className="font-mono text-muted-foreground">{w.display_ratio}</span>,
    },
    {
      group: 'Identification & Contract',
      label: 'Expiry Date',
      sublabel: 'Last trading day before contract rights cease and warrant expires',
      getValue: (w) => <span className="font-mono text-foreground">{w.expiry_date}</span>,
    },
    {
      group: 'Identification & Contract',
      label: 'Days to Expiry',
      sublabel: 'Calendar days remaining until maturity (theta decay accelerates below 30d)',
      getValue: (w) => <span className="font-mono text-muted-foreground">{w.display_days_to_expiry ?? 'N/A'}</span>,
    },

    // Quotes & Trading Friction
    {
      group: 'Quotes & Trading Costs',
      label: 'Bid / Ask Quotes',
      sublabel: 'Live market maker quotes: sell instantly at Bid, buy from issuer at Ask',
      getValue: (w) => (
        <span className="font-mono font-medium text-foreground">
          {w.display_bid ?? '—'} / {w.display_ask ?? '—'}
        </span>
      ),
    },
    {
      group: 'Quotes & Trading Costs',
      label: 'Mid Price',
      sublabel: 'Theoretical fair mid-market center price: (Bid + Ask) / 2',
      getValue: (w) => <span className="font-mono text-muted-foreground">{w.display_mid ?? '—'}</span>,
    },
    {
      group: 'Quotes & Trading Costs',
      label: 'Bid-Ask Spread %',
      sublabel: 'Immediate round-trip toll ((Ask - Bid) / Mid) incurred on entry & exit',
      getValue: (w) => {
        const wide = (w.spread_pct ?? 0) > 0.1;
        return (
          <span
            className={cn(
              'font-mono font-semibold',
              wide ? 'text-amber-600 dark:text-amber-400' : 'text-foreground'
            )}
          >
            {w.display_spread_pct ?? 'N/A'}
          </span>
        );
      },
    },

    // Quant Metrics
    {
      group: 'Quant Metrics',
      label: 'Effective Gearing',
      sublabel: 'True leverage multiplier: estimated % warrant move for every 1% stock move',
      getValue: (w) => (
        <span className="font-mono font-bold text-foreground">
          {w.display_effective_gearing ?? 'N/A'}
        </span>
      ),
    },
    {
      group: 'Quant Metrics',
      label: 'Headline Implied Vol (mid)',
      sublabel: 'Annualized expected volatility priced by issuer (higher IV = richer option premium)',
      getValue: (w) => (
        <span className="font-mono font-medium text-foreground">
          {w.display_headline_iv ?? 'N/A'}
        </span>
      ),
    },

    // Holding Friction
    {
      group: `Holding Friction (${holdingDays} Days)`,
      label: 'Spread Cost',
      sublabel: 'Fixed round-trip friction surrendered immediately to the market maker spread',
      getValue: (w) => (
        <span className="font-mono text-foreground">{w.display_spread_cost ?? 'N/A'}</span>
      ),
    },
    {
      group: `Holding Friction (${holdingDays} Days)`,
      label: 'Flat Underlying Decay',
      sublabel: `Cumulative theta cash lost if the underlying stock remains stationary over ${holdingDays}d`,
      getValue: (w) => (
        <span className="font-mono text-rose-600 dark:text-rose-400 font-medium">
          {w.display_flat_decay ?? 'N/A'}
        </span>
      ),
    },
    {
      group: `Holding Friction (${holdingDays} Days)`,
      label: 'IV Crush Estimate (-5 pts)',
      sublabel: 'Projected % price drop if the issuer lowers implied volatility by 5.0 points',
      getValue: (w) => (
        <span className="font-mono text-amber-600 dark:text-amber-400">
          {w.display_iv_crush ?? 'N/A'}
        </span>
      ),
    },
    {
      group: `Holding Friction (${holdingDays} Days)`,
      label: 'Breakeven Share Move',
      sublabel: `Minimum % move needed in underlying stock over ${holdingDays}d to overcome friction`,
      getValue: (w) => (
        <span className="font-mono font-bold text-foreground">
          {w.display_breakeven_move ?? 'N/A'}
        </span>
      ),
    },

    // Risk Flags
    {
      group: 'Active Risk Flags',
      label: 'Triggered Flags',
      sublabel: 'Evaluated structural risk warnings (wide spread, extreme gearing, steep decay)',
      getValue: (w) => {
        if (!w.flags || w.flags.length === 0) {
          return (
            <span className="inline-flex items-center rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
              No flags triggered
            </span>
          );
        }
        return (
          <div className="flex flex-wrap gap-1.5">
            {w.flags.map((f) => (
              <span
                key={f.code}
                title={f.text}
                className={cn(
                  'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-mono font-bold',
                  f.severity === 'high'
                    ? 'bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-500/30'
                    : 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30'
                )}
              >
                <ShieldAlert className="h-2.5 w-2.5" />
                <span>{f.code}</span>
              </span>
            ))}
          </div>
        );
      },
    },
  ];

  // Group rows by category
  const groups = Array.from(new Set(rows.map((r) => r.group)));

  return (
    <div
      className={cn(
        'overflow-hidden rounded-xl border border-border/80 bg-card shadow-xs',
        className
      )}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          {/* Header Row: Warrant Codes */}
          <thead>
            <tr className="border-b border-border/80 bg-muted/40">
              <th className="py-3 px-4 text-left font-semibold text-muted-foreground w-1/4">
                Attribute
              </th>
              {warrants.map((w) => (
                <th
                  key={w.code}
                  className="py-3 px-4 text-left font-mono font-bold text-foreground text-sm"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <span>{w.code}</span>
                      {onInspectWarrant && (
                        <button
                          type="button"
                          onClick={() => onInspectWarrant(w.code)}
                          title={`Inspect ${w.code} on Warrant Card`}
                          className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-all"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                    {onRemoveWarrant && warrants.length > 2 && (
                      <button
                        type="button"
                        onClick={() => onRemoveWarrant(w.code)}
                        title={`Remove ${w.code}`}
                        className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-all"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          {/* Grouped Rows */}
          <tbody className="divide-y divide-border/40">
            {groups.map((group) => {
              const groupRows = rows.filter((r) => r.group === group);
              return (
                <React.Fragment key={group}>
                  {/* Category Header */}
                  <tr className="bg-muted/30">
                    <td
                      colSpan={warrants.length + 1}
                      className="py-2 px-4 text-[11px] font-bold uppercase tracking-wider text-muted-foreground"
                    >
                      {group}
                    </td>
                  </tr>

                  {/* Attribute Rows */}
                  {groupRows.map((r) => (
                    <tr
                      key={r.label}
                      className="hover:bg-muted/20 transition-colors"
                    >
                      <td className="py-2.5 px-4 text-muted-foreground">
                        <div className="font-medium text-foreground">{r.label}</div>
                        {r.sublabel && (
                          <div className="text-[10px] text-muted-foreground/75">
                            {r.sublabel}
                          </div>
                        )}
                      </td>
                      {warrants.map((w) => (
                        <td key={w.code} className="py-2.5 px-4 align-middle">
                          {r.getValue(w)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Constitution Principle III Footnote */}
      <div className="border-t border-border/40 bg-muted/20 px-4 py-2.5 text-[11px] text-muted-foreground">
        <strong>Constitution Principle III:</strong> Uniform fixed-attribute comparison. No ranking, scores, or &ldquo;best&rdquo; labels are applied.
      </div>
    </div>
  );
};
