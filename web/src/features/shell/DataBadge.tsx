import React from 'react';
import { cn } from '../../lib/utils';
import { Radio, RotateCcw, Database, AlertTriangle, Clock } from 'lucide-react';

export type DataMode = 'live' | 'replay' | 'sample' | 'degraded' | 'stale';

export interface DataBadgeProps {
  mode: DataMode;
  asOf?: string;
  isStale?: boolean;
  marketOpen?: boolean;
  className?: string;
}

export const DataBadge: React.FC<DataBadgeProps> = ({
  mode,
  asOf,
  isStale = false,
  marketOpen,
  className,
}) => {
  const getBadgeConfig = () => {
    if (isStale) {
      return {
        label: 'Stale (>20m)',
        icon: Clock,
        classes: 'bg-amber-500/10 text-amber-500 border-amber-500/30',
        dot: 'bg-amber-500 animate-pulse',
      };
    }

    switch (mode) {
      case 'live': {
        const isClosed = marketOpen === false;
        return {
          label: isClosed ? 'Market Closed' : 'Live',
          icon: Radio,
          classes: isClosed
            ? 'bg-slate-500/10 text-slate-400 border-slate-500/20'
            : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
          dot: isClosed ? 'bg-slate-400' : 'bg-emerald-500 animate-pulse',
        };
      }
      case 'replay':
        return {
          label: 'Replay Mode',
          icon: RotateCcw,
          classes: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
          dot: 'bg-blue-500',
        };
      case 'sample':
        return {
          label: 'Sample Data',
          icon: Database,
          classes: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
          dot: 'bg-purple-500',
        };
      case 'degraded':
      default:
        return {
          label: 'Degraded',
          icon: AlertTriangle,
          classes: 'bg-rose-500/10 text-rose-500 border-rose-500/20',
          dot: 'bg-rose-500',
        };
    }
  };

  const config = getBadgeConfig();
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'inline-flex items-center space-x-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        config.classes,
        className
      )}
      title={asOf ? `Data as of: ${asOf}${isStale ? ' (Stale market data)' : ''}` : undefined}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', config.dot)} />
      <Icon className="h-3 w-3" />
      <span>{config.label}</span>
      {asOf && <span className="opacity-70 text-[10px]">({asOf})</span>}
    </div>
  );
};
