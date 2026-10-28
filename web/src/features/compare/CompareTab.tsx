import React, { useState, useEffect } from 'react';
import type { WarrantComparisonResult } from './types';
import { CompareGrid } from './CompareGrid';
import { cn } from '../../lib/utils';
import {
  Plus,
  RefreshCw,
  AlertCircle,
  Clock,
} from 'lucide-react';

export interface CompareTabProps {
  initialCodes?: string[];
  onInspectWarrant?: (code: string) => void;
  className?: string;
}

const DEFAULT_CODES = ['1155A1', '1155B1'];
const HOLDING_DAYS_PRESETS = [1, 3, 5, 10, 20];

export const CompareTab: React.FC<CompareTabProps> = ({
  initialCodes = DEFAULT_CODES,
  onInspectWarrant,
  className,
}) => {
  const [codes, setCodes] = useState<string[]>(initialCodes);
  const [codeInput, setCodeInput] = useState('');
  const [holdingDays, setHoldingDays] = useState(5);

  const [comparisonResult, setComparisonResult] = useState<WarrantComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync initialCodes if changed externally
  useEffect(() => {
    if (initialCodes && initialCodes.length >= 2) {
      setCodes(initialCodes.slice(0, 3));
    }
  }, [initialCodes]);

  // Fetch comparison from POST /api/compare
  useEffect(() => {
    let mounted = true;
    const fetchComparison = async () => {
      if (codes.length < 2) {
        setComparisonResult(null);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const resp = await fetch('/api/compare', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            codes,
            holding_days: holdingDays,
          }),
        });

        if (resp.ok) {
          const data: WarrantComparisonResult = await resp.json();
          if (mounted) {
            setComparisonResult(data);
          }
        } else {
          const errData = await resp.json().catch(() => ({}));
          const errMsg =
            errData.detail ||
            errData.error ||
            `Comparison request failed (HTTP ${resp.status})`;
          if (mounted) {
            setError(errMsg);
          }
        }
      } catch (err) {
        if (mounted) {
          setError('Network error while comparing warrants.');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchComparison();
    return () => {
      mounted = false;
    };
  }, [codes, holdingDays]);

  const handleAddCode = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = codeInput.trim().toUpperCase();
    if (!clean) return;

    if (codes.includes(clean)) {
      setCodeInput('');
      return;
    }

    if (codes.length >= 3) {
      setError('Comparison is limited to a maximum of 3 warrants.');
      return;
    }

    setCodes([...codes, clean]);
    setCodeInput('');
  };

  const handleRemoveCode = (codeToRemove: string) => {
    if (codes.length <= 2) {
      setError('Comparison requires at least 2 warrants.');
      return;
    }
    setCodes(codes.filter((c) => c !== codeToRemove));
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Top Controls: Input Codes and Holding Days */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border/70 bg-card p-4 shadow-xs">
        {/* Left: Code Add Form & Current Chips */}
        <div className="flex flex-wrap items-center gap-2 flex-1">
          <form onSubmit={handleAddCode} className="flex items-center gap-1.5">
            <input
              type="text"
              value={codeInput}
              onChange={(e) => setCodeInput(e.target.value)}
              placeholder="Add code (e.g. 1155C3)"
              className="w-40 rounded-lg border border-border bg-background py-1.5 px-3 text-xs font-mono font-medium text-foreground placeholder:text-muted-foreground focus:outline-hidden focus:ring-1 focus:ring-primary"
            />
            <button
              type="submit"
              disabled={codes.length >= 3 || !codeInput.trim()}
              className="inline-flex items-center gap-1 rounded-lg bg-primary px-2.5 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed shadow-xs"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Add</span>
            </button>
          </form>

          <span className="text-[11px] text-muted-foreground ml-1">
            ({codes.length}/3 warrants selected)
          </span>
        </div>

        {/* Right: Holding Days Stepper */}
        <div className="flex flex-col sm:items-end gap-1 text-xs">
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 text-[11px] font-medium text-foreground">
              <Clock className="h-3.5 w-3.5 text-rose-500" />
              Holding Horizon:
            </span>
            <div className="flex rounded-lg border border-border bg-card p-0.5 font-mono text-[11px]">
              {HOLDING_DAYS_PRESETS.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setHoldingDays(d)}
                  className={cn(
                    'rounded px-2.5 py-1 font-bold transition-all',
                    holdingDays === d
                      ? 'bg-primary text-primary-foreground shadow-xs'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  {d}d
                </button>
              ))}
            </div>
          </div>
          <span className="text-[10px] text-muted-foreground">
            Recalculates cumulative theta time decay and required breakeven share move over {holdingDays} day{holdingDays > 1 ? 's' : ''}.
          </span>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-start gap-2.5 rounded-xl border border-destructive/40 bg-destructive/10 p-3.5 text-xs text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="flex-1">{error}</div>
        </div>
      )}

      {/* Comparison Loading or Content */}
      {loading ? (
        <div className="flex items-center justify-center p-16 text-muted-foreground text-xs gap-2">
          <RefreshCw className="h-4 w-4 animate-spin text-primary" />
          <span>Calculating uniform comparison metrics...</span>
        </div>
      ) : comparisonResult ? (
        <CompareGrid
          warrants={comparisonResult.comparison}
          holdingDays={holdingDays}
          onRemoveWarrant={handleRemoveCode}
          onInspectWarrant={onInspectWarrant}
        />
      ) : null}
    </div>
  );
};
