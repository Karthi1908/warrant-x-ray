import React from 'react';
import { GLOSSARY, getGlossaryTerm } from '../../lib/glossary';
import { cn } from '../../lib/utils';
import { Info } from 'lucide-react';

export interface MetricPairProps {
  label: string;
  issuerValue?: string | null;
  recomputedValue?: string | null;
  diff?: number | null;
  diffText?: string | null;
  isMismatch?: boolean;
  glossaryKey?: keyof typeof GLOSSARY | string;
  basis?: string;
  className?: string;
}

export const MetricPair: React.FC<MetricPairProps> = ({
  label,
  issuerValue,
  recomputedValue,
  diffText,
  isMismatch = false,
  glossaryKey,
  basis,
  className,
}) => {
  const term = glossaryKey ? getGlossaryTerm(glossaryKey) : undefined;
  const hasDiff = Boolean(diffText);

  return (
    <div
      className={cn(
        'rounded-lg border border-border bg-card p-3 shadow-2xs hover:border-foreground/80 transition-colors',
        className
      )}
    >
      <div className="flex items-center justify-between gap-1 mb-2">
        <div className="flex items-center gap-1.5 text-xs font-bold text-muted-foreground">
          <span>{label}</span>
          {basis && (
            <span className="text-[10px] text-muted-foreground/80 font-mono">
              ({basis})
            </span>
          )}
          {term && (
            <span
              title={term.definition}
              aria-label={term.definition}
              className="inline-flex cursor-help text-muted-foreground/60 hover:text-foreground"
            >
              <Info className="h-3 w-3" />
            </span>
          )}
        </div>
        {hasDiff && (
          <span
            className={cn(
              'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-mono font-medium',
              isMismatch
                ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                : 'bg-muted text-muted-foreground border border-border/50'
            )}
          >
            {diffText}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="block text-[10px] text-muted-foreground/80 uppercase tracking-wider">
            Issuer
          </span>
          <span className="font-mono text-sm font-medium text-foreground">
            {issuerValue || '—'}
          </span>
        </div>
        <div>
          <span className="block text-[10px] text-muted-foreground/80 uppercase tracking-wider">
            Quant
          </span>
          <span className="font-mono text-sm font-semibold text-primary">
            {recomputedValue || '—'}
          </span>
        </div>
      </div>
    </div>
  );
};
