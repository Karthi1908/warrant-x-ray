import React from 'react';
import { cn } from '../../lib/utils';
import { RotateCcw, TrendingUp, Clock, Zap } from 'lucide-react';

export interface ScenarioValues {
  move: number;
  days: number;
  ivShift: number;
}

export interface ScenarioSlidersProps {
  move: number;
  days: number;
  ivShift: number;
  maxDays?: number;
  onChange?: (values: ScenarioValues) => void;
  onReset?: () => void;
  onPresetSelect?: (preset: ScenarioValues) => void;
  disabled?: boolean;
  className?: string;
}

export const PRESET_OPTIONS = [
  {
    label: 'Bullish: +5% in 3d',
    values: { move: 0.05, days: 3, ivShift: -5.0 },
  },
  {
    label: 'Flat Decay: 0% in 5d',
    values: { move: 0.0, days: 5, ivShift: 0.0 },
  },
  {
    label: 'IV Crush: 0% in 0d, -10 pts',
    values: { move: 0.0, days: 0, ivShift: -10.0 },
  },
];

export const ScenarioSliders: React.FC<ScenarioSlidersProps> = ({
  move,
  days,
  ivShift,
  maxDays = 60,
  onChange,
  onReset,
  onPresetSelect,
  disabled = false,
  className,
}) => {
  const handleMoveChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newMove = parseFloat(e.target.value) / 100.0;
    onChange?.({ move: newMove, days, ivShift });
  };

  const handleDaysChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newDays = parseInt(e.target.value, 10);
    onChange?.({ move, days: newDays, ivShift });
  };

  const handleIvChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newIv = parseFloat(e.target.value);
    onChange?.({ move, days, ivShift: newIv });
  };

  const handlePresetClick = (preset: ScenarioValues) => {
    if (onPresetSelect) {
      onPresetSelect(preset);
    } else {
      onChange?.(preset);
    }
  };

  return (
    <div className={cn('space-y-5 rounded-xl border border-border bg-card p-4 shadow-sm', className)}>
      <div className="flex items-center justify-between border-b border-border/60 pb-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-foreground">Scenario Simulator</h3>
          <p className="text-[11px] text-muted-foreground">Test "what has to go right" for payoff</p>
        </div>
        <button
          type="button"
          onClick={onReset}
          disabled={disabled}
          className="inline-flex items-center space-x-1.5 rounded-lg border border-border bg-muted/30 px-2.5 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-50"
          aria-label="Reset sliders"
        >
          <RotateCcw className="h-3 w-3" />
          <span>Reset</span>
        </button>
      </div>

      {/* Preset shortcuts */}
      <div className="space-y-1.5">
        <span className="text-[11px] font-medium text-muted-foreground">Scenario Presets:</span>
        <div className="flex flex-wrap gap-2">
          {PRESET_OPTIONS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              disabled={disabled}
              onClick={() => handlePresetClick(preset.values)}
              className={cn(
                'rounded-lg border border-border/80 bg-background px-2.5 py-1 text-xs font-medium transition-all',
                'hover:border-primary/40 hover:bg-primary/5 hover:text-foreground',
                'focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50'
              )}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Slider 1: Underlying Stock Move */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-1.5 font-medium text-foreground">
            <TrendingUp className="h-3.5 w-3.5 text-primary" />
            <span>Underlying Stock Move</span>
          </div>
          <span
            className={cn(
              'font-mono font-semibold px-1.5 py-0.5 rounded text-[11px]',
              move > 0
                ? 'bg-emerald-500/10 text-emerald-500'
                : move < 0
                ? 'bg-destructive/10 text-destructive'
                : 'bg-muted text-muted-foreground'
            )}
          >
            {move > 0 ? `+${(move * 100).toFixed(1)}%` : `${(move * 100).toFixed(1)}%`}
          </span>
        </div>
        <input
          type="range"
          min={-20}
          max={20}
          step={0.5}
          value={Math.round(move * 1000) / 10}
          disabled={disabled}
          onChange={handleMoveChange}
          className="w-full h-1.5 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
        />
        <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
          <span>-20%</span>
          <span>0%</span>
          <span>+20%</span>
        </div>
      </div>

      {/* Slider 2: Holding Period */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-1.5 font-medium text-foreground">
            <Clock className="h-3.5 w-3.5 text-primary" />
            <span>Holding Period</span>
          </div>
          <span className="font-mono font-semibold px-1.5 py-0.5 rounded text-[11px] bg-muted text-foreground">
            {days === 0 ? 'Day 0 (Immediate)' : days === 1 ? '1 day' : `${days} days`}
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={maxDays}
          step={1}
          value={days}
          disabled={disabled}
          onChange={handleDaysChange}
          className="w-full h-1.5 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
        />
        <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
          <span>0d</span>
          <span>{Math.round(maxDays / 2)}d</span>
          <span>{maxDays}d (Expiry)</span>
        </div>
      </div>

      {/* Slider 3: Implied Volatility Shift */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-1.5 font-medium text-foreground">
            <Zap className="h-3.5 w-3.5 text-primary" />
            <span>Implied Volatility Shift</span>
          </div>
          <span
            className={cn(
              'font-mono font-semibold px-1.5 py-0.5 rounded text-[11px]',
              ivShift > 0
                ? 'bg-emerald-500/10 text-emerald-500'
                : ivShift < 0
                ? 'bg-amber-500/10 text-amber-500'
                : 'bg-muted text-muted-foreground'
            )}
          >
            {ivShift > 0 ? `+${ivShift.toFixed(1)} pts` : `${ivShift.toFixed(1)} pts`}
          </span>
        </div>
        <input
          type="range"
          min={-15}
          max={15}
          step={0.5}
          value={ivShift}
          disabled={disabled}
          onChange={handleIvChange}
          className="w-full h-1.5 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
        />
        <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
          <span>-15 pts</span>
          <span>0 pts</span>
          <span>+15 pts</span>
        </div>
      </div>
    </div>
  );
};
