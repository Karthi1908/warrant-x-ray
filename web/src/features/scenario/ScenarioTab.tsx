import React, { useState, useEffect, useRef } from 'react';
import { cn } from '../../lib/utils';
import { ScenarioSliders, type ScenarioValues } from './ScenarioSliders';
import { PnlChart } from './PnlChart';
import { AssumptionsNote } from './AssumptionsNote';


export interface ScenarioTabProps {
  warrantCode: string;
  maxDays?: number;
  initialMove?: number;
  initialDays?: number;
  initialIvShift?: number;
  className?: string;
}

export interface ScenarioApiResult {
  entry_price: number;
  display_entry_price: string;
  exit_price: number;
  display_exit_price: string;
  pnl_pct: number;
  display_pnl_pct: string;
  breakeven_move?: number | null;
  display_breakeven_move?: string | null;
  curve: any[];
  assumptions: string[];
}

export const ScenarioTab: React.FC<ScenarioTabProps> = ({
  warrantCode,
  maxDays = 60,
  initialMove = 0.05,
  initialDays = 3,
  initialIvShift = -5.0,
  className,
}) => {
  const [values, setValues] = useState<ScenarioValues>({
    move: initialMove,
    days: initialDays,
    ivShift: initialIvShift,
  });

  const [result, setResult] = useState<ScenarioApiResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchScenario = async (vals: ScenarioValues) => {
    if (!warrantCode) {
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setIsLoading(true);
    setError(null);

    try {
      const resp = await fetch('/api/scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: warrantCode,
          move: vals.move,
          days: vals.days,
          iv_shift: vals.ivShift,
        }),
        signal: abortController.signal,
      });

      if (!resp.ok) {
        let msg = `Scenario calculation failed (${resp.status})`;
        try {
          const errData = await resp.json();
          if (errData?.error?.message) {
            msg = errData.error.message;
          } else if (errData?.message) {
            msg = errData.message;
          }
        } catch {
          // use fallback msg
        }
        throw new Error(msg);
      }

      const data = await resp.json();
      setResult(data);
    } catch (err: unknown) {
      if (!abortController.signal.aborted) {
        setError(err instanceof Error ? err.message : 'Error simulating scenario');
      }
    } finally {
      if (abortControllerRef.current === abortController) {
        setIsLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchScenario(values);
  }, [warrantCode, values]);

  const handleReset = () => {
    const defaultVals = { move: 0.0, days: 0, ivShift: 0.0 };
    setValues(defaultVals);
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Quick Scenario Preset Pills */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-xl border-2 border-border bg-card shadow-xs">
        <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
          <span>⚡</span> Quick Simulation Presets:
        </span>
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => setValues({ move: 0.05, days: 3, ivShift: 0.0 })}
            className="rounded-lg border-2 border-border bg-card px-2.5 py-1 text-xs font-bold text-emerald-800 dark:text-emerald-300 hover:bg-emerald-500/10 transition-all shadow-2xs"
          >
            🚀 Bullish (+5%, 3d)
          </button>
          <button
            type="button"
            onClick={() => setValues({ move: 0.10, days: 5, ivShift: 2.0 })}
            className="rounded-lg border-2 border-border bg-card px-2.5 py-1 text-xs font-bold text-indigo-800 dark:text-indigo-300 hover:bg-indigo-500/10 transition-all shadow-2xs"
          >
            ⚡ Rally (+10%, 5d)
          </button>
          <button
            type="button"
            onClick={() => setValues({ move: 0.0, days: 10, ivShift: -5.0 })}
            className="rounded-lg border-2 border-border bg-card px-2.5 py-1 text-xs font-bold text-amber-800 dark:text-amber-300 hover:bg-amber-500/10 transition-all shadow-2xs"
          >
            ⏳ Theta Trap (0%, 10d)
          </button>
          <button
            type="button"
            onClick={() => setValues({ move: -0.05, days: 3, ivShift: 0.0 })}
            className="rounded-lg border-2 border-border bg-card px-2.5 py-1 text-xs font-bold text-rose-800 dark:text-rose-300 hover:bg-rose-500/10 transition-all shadow-2xs"
          >
            🔻 Dip (-5%, 3d)
          </button>
        </div>
      </div>

      {/* Top 4 KPI metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-xl border-2 border-border bg-card p-3.5 shadow-xs border-l-4 border-l-blue-600">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Entry Price (Ask)
          </span>
          <div className="text-lg font-mono font-bold text-foreground mt-1">
            {result?.display_entry_price || '—'}
          </div>
        </div>

        <div className="rounded-xl border-2 border-border bg-card p-3.5 shadow-xs border-l-4 border-l-indigo-600">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Theoretical Exit
          </span>
          <div className="text-lg font-mono font-bold text-foreground mt-1">
            {result?.display_exit_price || '—'}
          </div>
        </div>

        <div className={cn(
          'rounded-xl border-2 border-border bg-card p-3.5 shadow-xs border-l-4',
          (result?.pnl_pct || 0) >= 0 ? 'border-l-emerald-600' : 'border-l-rose-600'
        )}>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Warrant P&L
          </span>
          <div
            className={cn(
              'text-lg font-mono font-bold mt-1',
              (result?.pnl_pct || 0) > 0
                ? 'text-emerald-700 dark:text-emerald-400'
                : (result?.pnl_pct || 0) < 0
                ? 'text-rose-700 dark:text-rose-400'
                : 'text-muted-foreground'
            )}
          >
            {result?.display_pnl_pct || '—'}
          </div>
        </div>

        <div className="rounded-xl border-2 border-border bg-card p-3.5 shadow-xs border-l-4 border-l-amber-600">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Breakeven Move
          </span>
          <div className="text-lg font-mono font-bold text-amber-700 dark:text-amber-400 mt-1">
            {result?.display_breakeven_move || '—'}
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-2.5 text-xs text-destructive">
          {error}
        </div>
      )}

      {/* Sliders & Controls */}
      <ScenarioSliders
        move={values.move}
        days={values.days}
        ivShift={values.ivShift}
        maxDays={maxDays}
        onChange={(v) => setValues(v)}
        onReset={handleReset}
        onPresetSelect={(p) => setValues(p)}
        disabled={isLoading}
      />

      {/* Curves & Charts */}
      {result?.curve && (
        <PnlChart
          curves={result.curve}
          breakevenMove={result.breakeven_move}
          displayBreakeven={result.display_breakeven_move}
          currentMove={values.move}
          currentPnl={result.pnl_pct}
        />
      )}

      {/* Assumptions */}
      {result?.assumptions && <AssumptionsNote assumptions={result.assumptions} />}
    </div>
  );
};
