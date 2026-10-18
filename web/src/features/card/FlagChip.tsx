import React from 'react';
import type { FlagItemData } from './types';
import { cn } from '../../lib/utils';
import { AlertCircle, AlertTriangle } from 'lucide-react';

export interface FlagChipProps {
  flag: FlagItemData;
  onClick?: () => void;
  className?: string;
}

export const FlagChip: React.FC<FlagChipProps> = ({
  flag,
  onClick,
  className,
}) => {
  const isHigh = flag.severity === 'high';

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium border transition-colors cursor-pointer text-left',
        isHigh
          ? 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/30 hover:bg-rose-500/15'
          : 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30 hover:bg-amber-500/15',
        className
      )}
      title={`${flag.code}: ${flag.text}`}
      aria-label={`${flag.code} risk flag, severity ${flag.severity}`}
    >
      {isHigh ? (
        <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-rose-500" />
      ) : (
        <AlertCircle className="h-3.5 w-3.5 shrink-0 text-amber-500" />
      )}
      <span className="font-semibold tracking-wide font-mono text-[11px]">
        {flag.code}
      </span>
      {flag.value && (
        <span className="opacity-80 font-mono text-[10px]">
          ({String(flag.value)})
        </span>
      )}
    </button>
  );
};
