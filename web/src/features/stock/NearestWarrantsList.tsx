import React from 'react';
import type { NearestWarrant } from './types';
import { cn } from '../../lib/utils';
import { Target, ArrowRight, Check } from 'lucide-react';

export interface NearestWarrantsListProps {
  nearest: NearestWarrant[];
  selectedCodes: string[];
  onToggleSelect: (code: string) => void;
  onInspect?: (code: string) => void;
  className?: string;
}

export const NearestWarrantsList: React.FC<NearestWarrantsListProps> = ({
  nearest,
  selectedCodes,
  onToggleSelect,
  onInspect,
  className,
}) => {
  if (nearest.length === 0) {
    return null;
  }

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <Target className="h-4 w-4 text-primary" />
          Nearest to the Money (Atm Candidates)
        </h3>
        <span className="text-[11px] text-muted-foreground">
          Sorted by absolute distance to share price
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {nearest.map((w) => {
          const isSelected = selectedCodes.includes(w.code);
          const isCall = w.type.toLowerCase() === 'call';

          return (
            <div
              key={w.code}
              className={cn(
                'group relative flex flex-col justify-between rounded-xl border p-3.5 transition-all',
                isSelected
                  ? 'border-primary bg-primary/5 shadow-xs'
                  : 'border-border/60 bg-card/60 hover:border-border hover:bg-card'
              )}
            >
              <div>
                <div className="flex items-center justify-between gap-1 mb-2">
                  <span className="font-mono text-sm font-bold text-foreground">
                    {w.code}
                  </span>
                  <span
                    className={cn(
                      'rounded px-1.5 py-0.5 text-[10px] font-bold font-mono uppercase',
                      isCall
                        ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                        : 'bg-purple-500/15 text-purple-600 dark:text-purple-400'
                    )}
                  >
                    {w.type}
                  </span>
                </div>

                <div className="space-y-1 text-xs">
                  <div className="flex justify-between text-muted-foreground">
                    <span>Strike:</span>
                    <span className="font-mono font-medium text-foreground">
                      {w.display_strike}
                    </span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span>Diff:</span>
                    <span className="font-mono font-medium text-foreground">
                      ±{w.display_distance_from_strike}
                    </span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span>Days left:</span>
                    <span className="font-mono text-foreground">
                      {w.display_days_to_expiry ?? 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span>Eff. Gearing:</span>
                    <span className="font-mono text-foreground">
                      {w.display_effective_gearing ?? 'N/A'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-3 pt-2.5 border-t border-border/40 flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() => onToggleSelect(w.code)}
                  className={cn(
                    'flex-1 inline-flex items-center justify-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition-all',
                    isSelected
                      ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                      : 'border border-border/60 bg-muted/30 text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                >
                  {isSelected ? (
                    <>
                      <Check className="h-3 w-3" />
                      <span>Selected</span>
                    </>
                  ) : (
                    <span>Compare</span>
                  )}
                </button>

                {onInspect && (
                  <button
                    type="button"
                    onClick={() => onInspect(w.code)}
                    title={`Inspect ${w.code} on Warrant Card`}
                    className="rounded-md border border-border/60 bg-muted/30 p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-all"
                  >
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
