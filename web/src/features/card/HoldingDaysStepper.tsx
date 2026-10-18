import React from 'react';
import { cn } from '../../lib/utils';
import { Minus, Plus, Calendar } from 'lucide-react';

export interface HoldingDaysStepperProps {
  days: number;
  maxDays?: number;
  onChange: (days: number) => void;
  className?: string;
}

export const HoldingDaysStepper: React.FC<HoldingDaysStepperProps> = ({
  days,
  maxDays = 90,
  onChange,
  className,
}) => {
  const clamp = (val: number) => Math.max(1, Math.min(maxDays, val));

  const handleDec = () => {
    if (days > 1) {
      onChange(clamp(days - 1));
    }
  };

  const handleInc = () => {
    if (days < maxDays) {
      onChange(clamp(days + 1));
    }
  };

  const presets = [1, 3, 5, 10, 20].filter((p) => p <= maxDays);

  return (
    <div
      className={cn(
        'flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-card p-3 shadow-xs',
        className
      )}
    >
      <div className="flex items-center gap-2">
        <Calendar className="h-4 w-4 text-muted-foreground" />
        <span className="text-xs font-medium text-foreground">
          Holding Horizon
        </span>
      </div>

      <div className="flex items-center gap-2">
        {/* Quick Presets */}
        <div className="hidden sm:flex items-center gap-1 mr-2">
          {presets.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => onChange(p)}
              className={cn(
                'rounded-md px-2 py-0.5 text-xs font-mono transition-colors',
                days === p
                  ? 'bg-primary text-primary-foreground font-semibold'
                  : 'bg-muted/80 text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              {p}d
            </button>
          ))}
        </div>

        {/* Stepper Controls */}
        <div className="flex items-center rounded-lg border border-border bg-background p-0.5 shadow-xs">
          <button
            type="button"
            onClick={handleDec}
            disabled={days <= 1}
            aria-label="Decrease holding days"
            className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-40 disabled:pointer-events-none transition-colors"
          >
            <Minus className="h-3.5 w-3.5" />
          </button>

          <span className="w-12 text-center font-mono text-xs font-semibold text-foreground">
            {days} {days === 1 ? 'day' : 'days'}
          </span>

          <button
            type="button"
            onClick={handleInc}
            disabled={days >= maxDays}
            aria-label="Increase holding days"
            className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-40 disabled:pointer-events-none transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
