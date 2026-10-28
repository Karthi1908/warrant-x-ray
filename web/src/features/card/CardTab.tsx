import React, { useState } from 'react';
import type { WarrantCardData } from './types';
import { MetricPair } from './MetricPair';
import { HoldingCostBar } from './HoldingCostBar';
import { FlagChip } from './FlagChip';
import { FlagDrawer } from './FlagDrawer';
import { HoldingDaysStepper } from './HoldingDaysStepper';
import { cn } from '../../lib/utils';
import {
  AlertTriangle,
  Clock,
  ShieldCheck,
  Building2,
  Calendar,
  Layers,
  Activity,
  BadgeAlert,
  Sliders,
  GitCompare,
} from 'lucide-react';

export interface CardTabProps {
  card: WarrantCardData;
  onHoldingDaysChange?: (days: number) => void;
  onSimulate?: (code: string) => void;
  onCompare?: (code: string) => void;
  className?: string;
}

export const CardTab: React.FC<CardTabProps> = ({
  card,
  onHoldingDaysChange,
  onSimulate,
  onCompare,
  className,
}) => {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [internalDays, setInternalDays] = useState(card.holding_days || 5);

  // Sync internalDays if card changes externally
  React.useEffect(() => {
    if (card.holding_days && card.holding_days !== internalDays) {
      setInternalDays(card.holding_days);
    }
  }, [card.holding_days, card.code]);

  const handleDaysChange = (days: number) => {
    setInternalDays(days);
    if (onHoldingDaysChange) {
      onHoldingDaysChange(days);
    }
  };

  // Dynamically compute holding cost presets for internalDays
  const dynamicPresets = React.useMemo(() => {
    const basePresets = card.presets || {};
    const baseDays = card.holding_days || 1;
    const days = internalDays;

    // Daily theta decay rate
    let dailyDecayRate = 0;
    if (card.metrics?.theta_per_day != null && card.metrics?.mid && card.metrics.mid > 0) {
      dailyDecayRate = Math.abs(card.metrics.theta_per_day) / card.metrics.mid;
    } else if (basePresets.flat_decay != null && baseDays > 0) {
      dailyDecayRate = basePresets.flat_decay / baseDays;
    }

    const flatDecay = dailyDecayRate * days;
    const spreadCost = basePresets.spread_cost ?? (card.metrics?.spread_pct ?? 0);
    const ivCrush = basePresets.iv_crush ?? 0;

    // Cumulative friction over holding horizon
    const effectiveGearing = card.metrics?.effective_gearing || 5.0;
    // Stock move needed to break even over holding horizon = (Spread + Flat Decay) / Effective Gearing
    const breakevenMove = effectiveGearing > 0 ? (spreadCost + flatDecay) / effectiveGearing : flatDecay;

    return {
      spread_cost: spreadCost,
      display_spread_cost: basePresets.display_spread_cost || `${(spreadCost * 100).toFixed(1)}%`,
      flat_decay: flatDecay,
      display_flat_decay: `${(flatDecay * 100).toFixed(1)}%`,
      iv_crush: ivCrush,
      display_iv_crush: basePresets.display_iv_crush || `${(ivCrush * 100).toFixed(1)}%`,
      gearing_check: effectiveGearing,
      display_gearing_check: `${effectiveGearing.toFixed(2)}x`,
      breakeven_move: breakevenMove,
      display_breakeven_move: `+${(breakevenMove * 100).toFixed(1)}%`,
    };
  }, [card, internalDays]);

  const isCall = card.type?.toLowerCase() === 'call';
  const daysLeft = card.metrics.days_to_expiry ?? 0;
  const isExpired = card.expired || daysLeft <= 0;

  // Cross-check differences
  const ivDiff = card.metrics.cross_check?.iv_diff_points;
  const egDiff = card.metrics.cross_check?.eg_diff_rel;
  const deltaDiff = card.metrics.cross_check?.delta_diff;

  const ivDiffText =
    ivDiff != null
      ? `Δ ${ivDiff >= 0 ? '+' : ''}${ivDiff.toFixed(1)} pts`
      : undefined;

  const egDiffText =
    egDiff != null
      ? `Δ ${egDiff >= 0 ? '+' : ''}${(egDiff * 100).toFixed(1)}%`
      : undefined;

  const deltaDiffText =
    deltaDiff != null
      ? `Δ ${deltaDiff >= 0 ? '+' : ''}${deltaDiff.toFixed(3)}`
      : undefined;

  return (
    <div className={cn('space-y-6', className)}>
      {/* Expired Warning Banner */}
      {isExpired && (
        <div className="flex items-center gap-2.5 rounded-xl border border-destructive/40 bg-destructive/10 p-3.5 text-xs text-destructive">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <div>
            <span className="font-semibold">This warrant has expired.</span>{' '}
            Trading and exercise rights have ceased. Forward-looking quant projections and Greeks are unavailable.
          </div>
        </div>
      )}

      {/* Header Banner */}
      <div className="rounded-xl border border-border bg-card p-5 shadow-xs">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-bold tracking-tight text-foreground font-mono">
                {card.code}
              </h2>
              <span
                className={cn(
                  'rounded-md px-2 py-0.5 text-xs font-bold uppercase tracking-wider font-mono',
                  isCall
                    ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30'
                    : 'bg-purple-500/15 text-purple-700 dark:text-purple-400 border border-purple-500/30'
                )}
              >
                {card.type.toUpperCase()}
              </span>
              <span className="rounded-md border border-border bg-muted/60 px-2 py-0.5 text-xs font-medium text-foreground">
                {card.underlying_ticker}
              </span>
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Building2 className="h-3.5 w-3.5" />
                {card.issuer}
              </span>
            </div>

            <p className="text-xs text-muted-foreground flex items-center gap-2 pt-0.5">
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                Expiry: {card.expiry_date}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1 font-mono">
                <Clock className="h-3 w-3" />
                {card.metrics.display_days_to_expiry || `${daysLeft} days`}
              </span>
            </p>
          </div>

          <div className="flex items-center gap-3 text-right">
            <div>
              <span className="block text-[10px] text-muted-foreground uppercase tracking-wider">
                Underlying {card.underlying_ticker}
              </span>
              <span className="font-mono text-base font-semibold text-foreground">
                {card.display_underlying_price || '—'}
              </span>
            </div>
            {(onSimulate || onCompare) && (
              <div className="flex items-center gap-2 pl-3 border-l border-border/60">
                {onSimulate && (
                  <button
                    type="button"
                    onClick={() => onSimulate(card.code)}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 text-xs font-semibold shadow-xs transition-colors"
                  >
                    <Sliders className="h-3.5 w-3.5" />
                    <span>Simulate</span>
                  </button>
                )}
                {onCompare && (
                  <button
                    type="button"
                    onClick={() => onCompare(card.code)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-muted/60 hover:bg-muted text-foreground px-3 py-1.5 text-xs font-semibold transition-colors"
                  >
                    <GitCompare className="h-3.5 w-3.5" />
                    <span>Compare</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Core Specs Strip */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 border-t border-border/70 pt-4 text-xs">
          <div className="rounded-lg bg-muted/20 p-2.5 flex flex-col justify-between">
            <div>
              <span className="block text-[11px] font-semibold text-muted-foreground">Strike Price</span>
              <span className="font-mono text-sm font-bold text-foreground">
                {card.display_strike}
              </span>
            </div>
            <p className="mt-1 text-[10px] text-muted-foreground leading-tight">
              Target exercise price {card.underlying_ticker} must surpass by expiry to finish in-the-money.
            </p>
          </div>

          <div className="rounded-lg bg-muted/20 p-2.5 flex flex-col justify-between">
            <div>
              <span className="block text-[11px] font-semibold text-muted-foreground">Exercise Ratio</span>
              <span className="font-mono text-sm font-bold text-foreground">
                {card.display_ratio}
              </span>
            </div>
            <p className="mt-1 text-[10px] text-muted-foreground leading-tight">
              Number of warrants required to entitle exposure to 1 underlying share.
            </p>
          </div>

          <div className="rounded-lg bg-muted/20 p-2.5 flex flex-col justify-between">
            <div>
              <span className="block text-[11px] font-semibold text-muted-foreground">Bid / Ask</span>
              <span className="font-mono text-sm font-bold text-foreground flex items-center gap-1">
                <span>{card.display_bid || '—'}</span>
                <span className="text-muted-foreground/60">/</span>
                <span>{card.display_ask || '—'}</span>
              </span>
            </div>
            <p className="mt-1 text-[10px] text-muted-foreground leading-tight">
              Market maker quotes: sell instantly at Bid, buy from issuer at Ask.
            </p>
          </div>

          <div className="rounded-lg bg-muted/20 p-2.5 flex flex-col justify-between">
            <div>
              <span className="block text-[11px] font-semibold text-muted-foreground">Spread Friction</span>
              <span className="font-mono text-sm font-bold text-amber-600 dark:text-amber-400">
                {card.metrics.display_spread_pct || '—'}
              </span>
            </div>
            <p className="mt-1 text-[10px] text-muted-foreground leading-tight">
              Immediate round-trip loss: ((Ask - Bid) / Mid) incurred on day-one trading.
            </p>
          </div>
        </div>
      </div>

      {/* Risk Flags Section */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-1.5">
            <BadgeAlert className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Evaluated Risk Flags
            </h3>
          </div>
          <button
            type="button"
            onClick={() => setIsDrawerOpen(true)}
            className="text-xs font-medium text-primary hover:underline flex items-center gap-1"
          >
            <span>Risk Details ({card.flags.length} active)</span>
          </button>
        </div>

        {card.flags.length === 0 ? (
          <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-2.5 text-xs text-emerald-700 dark:text-emerald-400">
            <ShieldCheck className="h-4 w-4 shrink-0" />
            <span>No risk flags triggered under current thresholds.</span>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {card.flags.map((flag) => (
              <FlagChip
                key={flag.code}
                flag={flag}
                onClick={() => setIsDrawerOpen(true)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Cost of Holding Presets & Stepper */}
      {!isExpired && (
        <div className="space-y-3">
          <HoldingDaysStepper
            days={internalDays}
            maxDays={Math.max(1, daysLeft || 90)}
            onChange={handleDaysChange}
          />
          <HoldingCostBar
            presets={dynamicPresets}
            holdingDays={internalDays}
            underlyingTicker={card.underlying_ticker}
          />
        </div>
      )}

      {/* Quant Cross-Check & Greeks */}
      {!isExpired && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5" />
              <span>Issuer vs Quant Cross-Check</span>
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <MetricPair
              label="Implied Volatility"
              issuerValue={
                card.metrics.cross_check?.iv_diff_points != null && card.metrics.headline_iv != null
                  ? `${((card.metrics.headline_iv * 100) - (card.metrics.cross_check.iv_diff_points)).toFixed(1)}%`
                  : undefined
              }
              recomputedValue={card.metrics.display_headline_iv}
              diff={ivDiff}
              diffText={ivDiffText}
              isMismatch={Math.abs(ivDiff ?? 0) >= 3.0}
              basis={card.metrics.headline_iv_basis || 'mid'}
              glossaryKey="implied_volatility"
              description="Annualized price volatility priced into the warrant quotes. Higher IV means more expensive option premium; divergence indicates potential issuer mispricing."
            />

            <MetricPair
              label="Effective Gearing"
              issuerValue={undefined}
              recomputedValue={card.metrics.display_effective_gearing}
              diff={egDiff}
              diffText={egDiffText}
              isMismatch={Math.abs(egDiff ?? 0) >= 0.1}
              glossaryKey="effective_gearing"
              description="Actual percentage price change in this warrant for every 1.0% move in the underlying stock. Takes option delta and ratio into account."
            />

            <MetricPair
              label="Delta (per share)"
              issuerValue={undefined}
              recomputedValue={card.metrics.display_delta_share}
              diff={deltaDiff}
              diffText={deltaDiffText}
              isMismatch={Math.abs(deltaDiff ?? 0) >= 0.05}
              glossaryKey="delta"
              description="Theoretical RM price change of the warrant for each RM 1.00 move in the underlying stock price."
            />
          </div>

          {/* Greeks and Pricing Row */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5" />
              <span>Analytical Greeks & Required Move</span>
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
              <div className="rounded-lg bg-muted/30 p-2.5 flex flex-col justify-between">
                <div>
                  <span className="block text-muted-foreground font-semibold text-[11px]">Gamma</span>
                  <span className="font-mono font-bold text-foreground text-sm">
                    {card.metrics.display_gamma || '—'}
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-muted-foreground leading-tight">
                  Rate of change in Delta per RM 1.00 stock move. Measures how fast leverage accelerates.
                </p>
              </div>

              <div className="rounded-lg bg-muted/30 p-2.5 flex flex-col justify-between">
                <div>
                  <span className="block text-muted-foreground font-semibold text-[11px]">Vega (per pt)</span>
                  <span className="font-mono font-bold text-foreground text-sm">
                    {card.metrics.display_vega_per_point || '—'}
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-muted-foreground leading-tight">
                  RM warrant price sensitivity per 1% change in implied volatility.
                </p>
              </div>

              <div className="rounded-lg bg-muted/30 p-2.5 flex flex-col justify-between">
                <div>
                  <span className="block text-muted-foreground font-semibold text-[11px]">Theta (per day)</span>
                  <span className="font-mono font-bold text-rose-600 dark:text-rose-400 text-sm">
                    {card.metrics.display_theta_per_day || '—'}
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-muted-foreground leading-tight">
                  Daily cash lost per warrant to time decay if the stock price remains unchanged.
                </p>
              </div>

              <div className="rounded-lg bg-muted/30 p-2.5 flex flex-col justify-between">
                <div>
                  <span className="block text-muted-foreground font-semibold text-[11px]">Premium</span>
                  <span className="font-mono font-bold text-foreground text-sm">
                    {card.metrics.display_premium || '—'}
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-muted-foreground leading-tight">
                  Extra % the stock must rise from current spot price to break even by expiry date.
                </p>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-border/60 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg border border-border/60 bg-muted/20 p-2.5 flex flex-col justify-between">
                <div>
                  <span className="text-muted-foreground text-[11px] block font-semibold">Breakeven at Expiry</span>
                  <span className="font-mono font-bold text-foreground text-sm">
                    {card.metrics.display_breakeven_price || '—'}
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-muted-foreground leading-tight">
                  The underlying stock price {card.underlying_ticker} must reach on {card.expiry_date} for zero net profit/loss.
                </p>
              </div>

              <div className="rounded-lg border border-border/60 bg-muted/20 p-2.5 flex flex-col justify-between">
                <div>
                  <span className="text-muted-foreground text-[11px] block font-semibold">Required Underlying Move</span>
                  <span className="font-mono font-bold text-primary text-sm">
                    {card.metrics.display_required_move || '—'}
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-muted-foreground leading-tight">
                  Minimum percentage rise from today's spot price required by expiry date to avoid losing 100%.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Provenance & Footer */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-4 text-[11px] text-muted-foreground">
        <div className="flex items-center gap-3">
          {card.evidence_id && (
            <span className="font-mono rounded bg-muted px-1.5 py-0.5">
              Evidence {card.evidence_id}
            </span>
          )}
          {card.mode && (
            <span className="uppercase font-mono">Mode: {card.mode}</span>
          )}
          {card.as_of && (
            <span>Snapshot: {new Date(card.as_of).toLocaleString()}</span>
          )}
        </div>
        <div className="italic">
          All metrics computed deterministically. Informational only, never advice.
        </div>
      </div>

      {/* Flag Drawer */}
      <FlagDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        flags={card.flags}
        notEvaluated={card.not_evaluated}
        warrantCode={card.code}
      />
    </div>
  );
};
