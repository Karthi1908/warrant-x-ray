import React, { useEffect } from 'react';
import type { FlagItemData, NotEvaluatedItemData } from './types';
import { cn } from '../../lib/utils';
import { X, AlertTriangle, AlertCircle, HelpCircle } from 'lucide-react';

export interface FlagDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  flags: FlagItemData[];
  notEvaluated: NotEvaluatedItemData[];
  warrantCode: string;
}

export const FlagDrawer: React.FC<FlagDrawerProps> = ({
  isOpen,
  onClose,
  flags,
  notEvaluated,
  warrantCode,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-background/80 backdrop-blur-xs animate-in fade-in-0 duration-200">
      {/* Backdrop click */}
      <div
        className="fixed inset-0"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer Panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="flag-drawer-title"
        className="relative z-10 flex h-full w-full max-w-md flex-col border-l border-border bg-card shadow-2xl p-6 overflow-y-auto"
      >
        <div className="flex items-center justify-between border-b border-border pb-4 mb-4">
          <div>
            <h2 id="flag-drawer-title" className="text-base font-semibold text-foreground">
              Risk Flags & Evaluations
            </h2>
            <p className="text-xs text-muted-foreground font-mono mt-0.5">
              Warrant {warrantCode}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close risk details"
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-6 flex-1">
          {/* Section 1: Triggered Flags */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Triggered Risk Flags ({flags.length})
              </h3>
            </div>

            {flags.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-4 text-center text-xs text-muted-foreground">
                No active risk flags triggered for this warrant under current market parameters.
              </div>
            ) : (
              <div className="space-y-3">
                {flags.map((flag) => {
                  const isHigh = flag.severity === 'high';
                  return (
                    <div
                      key={flag.code}
                      className={cn(
                        'rounded-xl border p-3.5 space-y-2',
                        isHigh
                          ? 'border-rose-500/30 bg-rose-500/5'
                          : 'border-amber-500/30 bg-amber-500/5'
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          {isHigh ? (
                            <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0" />
                          ) : (
                            <AlertCircle className="h-4 w-4 text-amber-500 shrink-0" />
                          )}
                          <span className="font-mono text-xs font-bold tracking-tight">
                            {flag.code}
                          </span>
                        </div>
                        <span
                          className={cn(
                            'rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase',
                            isHigh
                              ? 'bg-rose-500/20 text-rose-700 dark:text-rose-400'
                              : 'bg-amber-500/20 text-amber-700 dark:text-amber-400'
                          )}
                        >
                          {flag.severity}
                        </span>
                      </div>

                      <p className="text-xs text-foreground/90 font-medium leading-relaxed">
                        {flag.text}
                      </p>

                      <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-border/40 text-muted-foreground">
                        <div>
                          <span className="opacity-75">Threshold: </span>
                          <span className="font-mono">{String(flag.threshold)}</span>
                        </div>
                        {flag.value && (
                          <div>
                            <span className="opacity-75">Observed: </span>
                            <span className="font-mono font-medium text-foreground">
                              {String(flag.value)}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Section 2: Not Evaluated Flags */}
          <div className="space-y-3 pt-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <span>Not Evaluated ({notEvaluated.length})</span>
              <span title="A flag lacking required inputs is recorded as not_evaluated, never clear (FR-FLAG-02).">
                <HelpCircle className="h-3 w-3 text-muted-foreground/60" />
              </span>
            </h3>

            {notEvaluated.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-3 text-center text-xs text-muted-foreground">
                All standard risk conditions were evaluated against market data.
              </div>
            ) : (
              <div className="space-y-2">
                {notEvaluated.map((ne) => (
                  <div
                    key={ne.flag}
                    className="rounded-lg border border-border/60 bg-muted/30 p-2.5 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-semibold text-foreground/90 text-[11px]">
                        {ne.flag}
                      </span>
                      <span className="text-[10px] text-muted-foreground uppercase font-mono">
                        Not evaluated
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-snug">
                      {ne.reason}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-border pt-4 mt-6 text-[11px] text-muted-foreground">
          Risk flags are rule-based warnings derived from quantitative thresholds and do not represent trading recommendations.
        </div>
      </div>
    </div>
  );
};
