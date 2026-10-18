import React from 'react';
import type { WarrantListItem } from './types';
import { cn } from '../../lib/utils';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ShieldAlert,
  Search,
  ExternalLink,
} from 'lucide-react';

export type SortField =
  | 'strike'
  | 'expiry_date'
  | 'spread_pct'
  | 'effective_gearing'
  | 'headline_iv';

export interface WarrantTableProps {
  warrants: WarrantListItem[];
  selectedCodes: string[];
  onToggleSelect: (code: string) => void;
  onInspect?: (code: string) => void;
  sortField: SortField;
  sortOrder: 'asc' | 'desc';
  onSortChange: (field: SortField) => void;
  ivBasis: string;
  className?: string;
}

export const WarrantTable: React.FC<WarrantTableProps> = ({
  warrants,
  selectedCodes,
  onToggleSelect,
  onInspect,
  sortField,
  sortOrder,
  onSortChange,
  ivBasis,
  className,
}) => {
  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-3 w-3 text-muted-foreground/60" />;
    }
    return sortOrder === 'asc' ? (
      <ArrowUp className="h-3 w-3 text-primary" />
    ) : (
      <ArrowDown className="h-3 w-3 text-primary" />
    );
  };

  if (warrants.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/80 bg-muted/20 p-12 text-center">
        <Search className="mx-auto h-8 w-8 text-muted-foreground/60 mb-3" />
        <h4 className="text-sm font-semibold text-foreground">
          No Warrants Found for this Selection
        </h4>
        <p className="mt-1 text-xs text-muted-foreground max-w-md mx-auto">
          There are currently no listed structured warrants matching your filter criteria on this underlying stock.
        </p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'overflow-hidden rounded-xl border border-border/70 bg-card shadow-xs',
        className
      )}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-muted/50 border-b border-border/70 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider select-none">
            <tr>
              <th className="py-3 px-3 w-10 text-center">
                <span className="sr-only">Select</span>
              </th>
              <th className="py-3 px-3">Code</th>
              <th className="py-3 px-3">Issuer</th>
              <th className="py-3 px-3">Type</th>
              <th
                className="py-3 px-3 cursor-pointer hover:text-foreground transition-colors"
                onClick={() => onSortChange('strike')}
              >
                <div className="flex items-center gap-1">
                  <span>Strike</span>
                  {renderSortIcon('strike')}
                </div>
              </th>
              <th
                className="py-3 px-3 cursor-pointer hover:text-foreground transition-colors"
                onClick={() => onSortChange('expiry_date')}
              >
                <div className="flex items-center gap-1">
                  <span>Expiry / Days</span>
                  {renderSortIcon('expiry_date')}
                </div>
              </th>
              <th className="py-3 px-3 text-right">Bid / Ask</th>
              <th
                className="py-3 px-3 text-right cursor-pointer hover:text-foreground transition-colors"
                onClick={() => onSortChange('spread_pct')}
              >
                <div className="flex items-center justify-end gap-1">
                  <span>Spread</span>
                  {renderSortIcon('spread_pct')}
                </div>
              </th>
              <th
                className="py-3 px-3 text-right cursor-pointer hover:text-foreground transition-colors"
                onClick={() => onSortChange('effective_gearing')}
              >
                <div className="flex items-center justify-end gap-1">
                  <span>Eff. Gearing</span>
                  {renderSortIcon('effective_gearing')}
                </div>
              </th>
              <th
                className="py-3 px-3 text-right cursor-pointer hover:text-foreground transition-colors"
                onClick={() => onSortChange('headline_iv')}
              >
                <div className="flex items-center justify-end gap-1">
                  <span>IV ({ivBasis})</span>
                  {renderSortIcon('headline_iv')}
                </div>
              </th>
              <th className="py-3 px-3 text-center">Flags</th>
              <th className="py-3 px-3 text-center w-12">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40 font-mono">
            {warrants.map((w) => {
              const isSelected = selectedCodes.includes(w.code);
              const isCall = w.type.toLowerCase() === 'call';

              return (
                <tr
                  key={w.code}
                  className={cn(
                    'transition-colors hover:bg-muted/40',
                    isSelected && 'bg-primary/5'
                  )}
                >
                  <td className="py-2.5 px-3 text-center">
                    <input
                      type="checkbox"
                      aria-label={`Select ${w.code} for comparison`}
                      checked={isSelected}
                      disabled={!isSelected && selectedCodes.length >= 3}
                      onChange={() => onToggleSelect(w.code)}
                      className="rounded border-border text-primary focus:ring-primary h-4 w-4 cursor-pointer"
                    />
                  </td>
                  <td className="py-2.5 px-3 font-bold text-foreground">
                    {w.code}
                  </td>
                  <td className="py-2.5 px-3 font-sans font-medium text-muted-foreground">
                    {w.issuer}
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={cn(
                        'rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider font-mono border',
                        isCall
                          ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
                          : 'bg-purple-500/15 text-purple-700 dark:text-purple-400 border-purple-500/30'
                      )}
                    >
                      {w.type}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-semibold text-foreground">
                    {w.display_strike}
                  </td>
                  <td className="py-2.5 px-3 font-sans text-muted-foreground">
                    <div className="font-mono text-foreground font-medium">{w.expiry_date}</div>
                    <div className="text-[10px] text-muted-foreground">
                      {w.display_days_to_expiry ?? 'N/A'}
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <div className="font-semibold text-foreground">
                      {w.display_bid ?? '—'} / {w.display_ask ?? '—'}
                    </div>
                    {w.display_mid && (
                      <div className="text-[10px] text-muted-foreground">
                        Mid: {w.display_mid}
                      </div>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <span
                      className={cn(
                        'inline-block px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold border',
                        (w.spread_pct ?? 0) <= 0.05
                          ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20'
                          : (w.spread_pct ?? 0) <= 0.1
                          ? 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20'
                          : 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20 font-bold'
                      )}
                    >
                      {w.display_spread_pct ?? 'N/A'}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <span className="font-bold text-indigo-700 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/60 px-1.5 py-0.5 rounded border border-indigo-200/60 dark:border-indigo-800/40">
                      {w.display_effective_gearing ?? 'N/A'}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right font-medium text-foreground">
                    {w.display_headline_iv ?? 'N/A'}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    {(w.flags_count ?? 0) > 0 ? (
                      <span className="inline-flex items-center gap-1 rounded-md bg-rose-500/15 border border-rose-500/30 px-2 py-0.5 text-[10px] font-bold text-rose-700 dark:text-rose-400">
                        <ShieldAlert className="h-3 w-3" />
                        <span>{w.flags_count}</span>
                      </span>
                    ) : (
                      <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">Clean</span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    {onInspect && (
                      <button
                        type="button"
                        onClick={() => onInspect(w.code)}
                        title={`Inspect ${w.code} on Warrant Card`}
                        className="inline-flex items-center gap-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 hover:bg-primary hover:text-primary-foreground text-indigo-600 dark:text-indigo-400 px-2 py-1 text-[11px] font-semibold transition-all shadow-2xs border border-indigo-200/60 dark:border-indigo-800/40"
                      >
                        <ExternalLink className="h-3 w-3" />
                        <span>View</span>
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
