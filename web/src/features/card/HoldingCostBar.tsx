import React from 'react';
import type { HoldingCostPresetsData } from './types';
import { cn } from '../../lib/utils';
import { ShieldAlert, TrendingUp } from 'lucide-react';

export interface HoldingCostBarProps {
  presets: HoldingCostPresetsData;
  holdingDays: number;
  underlyingTicker: string;
  className?: string;
}

export const HoldingCostBar: React.FC<HoldingCostBarProps> = ({
  presets,
  holdingDays,
  underlyingTicker,
  className,
}) => {
  const spread = Math.max(0, presets.spread_cost ?? 0);
  const decay = Math.max(0, presets.flat_decay ?? 0);
  const crush = Math.max(0, presets.iv_crush ?? 0);
  const totalCost = spread + decay + crush;

  // Calculate percentage shares for the visual bar (normalized)
  const spreadShare = totalCost > 0 ? (spread / totalCost) * 100 : 33.3;
  const decayShare = totalCost > 0 ? (decay / totalCost) * 100 : 33.3;
  const crushShare = totalCost > 0 ? (crush / totalCost) * 100 : 33.4;

  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-card p-4 shadow-xs space-y-4',
        className
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-foreground flex items-center gap-1.5">
            <span>{holdingDays}-day Holding Cost Breakdown</span>
          </h3>
          <p className="text-xs text-muted-foreground">
            Frictional drag before factoring in underlying stock direction.
          </p>
        </div>
        {presets.display_breakeven_move && (
          <div className="flex items-center gap-1.5 rounded-lg bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary border border-primary/20">
            <TrendingUp className="h-3.5 w-3.5" />
            <span>
              Breakeven: {presets.display_breakeven_move} on {underlyingTicker}
            </span>
          </div>
        )}
      </div>

      {/* Visual Stacked Bar */}
      <div className="space-y-1.5">
        <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted/60 p-0.5">
          {spread > 0 && (
            <div
              style={{ width: `${spreadShare}%` }}
              className="bg-amber-500 rounded-l-full transition-all duration-300"
              title={`Spread cost: ${presets.display_spread_cost || ''}`}
            />
          )}
          {decay > 0 && (
            <div
              style={{ width: `${decayShare}%` }}
              className={cn(
                'bg-rose-500 transition-all duration-300',
                spread === 0 && 'rounded-l-full',
                crush === 0 && 'rounded-r-full'
              )}
              title={`Flat decay: ${presets.display_flat_decay || ''}`}
            />
          )}
          {crush > 0 && (
            <div
              style={{ width: `${crushShare}%` }}
              className="bg-purple-500 rounded-r-full transition-all duration-300"
              title={`IV crush: ${presets.display_iv_crush || ''}`}
            />
          )}
        </div>
      </div>

      {/* Detail Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between font-medium text-amber-700 dark:text-amber-400">
              <span className="font-semibold text-xs">Spread Friction</span>
              <span className="font-mono text-sm font-bold">
                {presets.display_spread_cost || '—'}
              </span>
            </div>
            <p className="mt-1.5 text-[11px] text-muted-foreground leading-relaxed">
              Immediate round-trip cost ((Ask - Bid) / Mid) surrendered upon entry and exit to the market maker spread before any price movement.
            </p>
          </div>
          <div className="mt-2 text-[10px] font-mono text-amber-700/80 dark:text-amber-400/80 bg-amber-500/10 px-1.5 py-0.5 rounded w-fit">
            Fixed trading toll
          </div>
        </div>

        <div className="rounded-lg border border-rose-500/20 bg-rose-500/5 p-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between font-medium text-rose-700 dark:text-rose-400">
              <span className="font-semibold text-xs">Theta Decay ({holdingDays}d)</span>
              <span className="font-mono text-sm font-bold">
                {presets.display_flat_decay || '—'}
              </span>
            </div>
            <p className="mt-1.5 text-[11px] text-muted-foreground leading-relaxed">
              Expected loss of warrant value over {holdingDays} day{holdingDays > 1 ? 's' : ''} purely from calendar time passage if {underlyingTicker} remains flat.
            </p>
          </div>
          <div className="mt-2 text-[10px] font-mono text-rose-700/80 dark:text-rose-400/80 bg-rose-500/10 px-1.5 py-0.5 rounded w-fit">
            Time erosion drag
          </div>
        </div>

        <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between font-medium text-purple-700 dark:text-purple-400">
              <span className="font-semibold text-xs">IV Crush (-5 pts)</span>
              <span className="font-mono text-sm font-bold">
                {presets.display_iv_crush || '—'}
              </span>
            </div>
            <p className="mt-1.5 text-[11px] text-muted-foreground leading-relaxed">
              Estimated percentage drop in warrant price if the issuer contracts implied volatility by 5.0 points (common after corporate events).
            </p>
          </div>
          <div className="mt-2 text-[10px] font-mono text-purple-700/80 dark:text-purple-400/80 bg-purple-500/10 px-1.5 py-0.5 rounded w-fit">
            Volatility compression
          </div>
        </div>
      </div>

      <div className="flex items-start gap-2 rounded-lg bg-muted/40 p-2.5 text-[11px] text-muted-foreground leading-relaxed">
        <ShieldAlert className="h-4 w-4 shrink-0 text-muted-foreground/80 mt-0.5" />
        <span>
          <strong>Holding Drag Rule:</strong> Time decay is non-linear and accelerates sharply as expiry nears. Over a {holdingDays}-day period, {underlyingTicker} must continuously advance to overcome the cumulative friction of round-trip spread toll and theta erosion.
        </span>
      </div>
    </div>
  );
};
