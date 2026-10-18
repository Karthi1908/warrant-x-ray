import React from 'react';
import { cn } from '../../lib/utils';
import { TrendingUp, TrendingDown, Layers, Zap } from 'lucide-react';

export interface MarketTickerItem {
  ticker: string;
  name: string;
  price: string;
  changePct: number;
  warrantCount: number;
  callCount: number;
  putCount: number;
}

export const BURSA_UNDERLYINGS: MarketTickerItem[] = [
  {
    ticker: 'MAYBANK',
    name: 'Malayan Banking',
    price: 'RM 10.50',
    changePct: 0.48,
    warrantCount: 12,
    callCount: 7,
    putCount: 5,
  },
  {
    ticker: 'CIMB',
    name: 'CIMB Group',
    price: 'RM 7.30',
    changePct: 1.11,
    warrantCount: 10,
    callCount: 6,
    putCount: 4,
  },
  {
    ticker: 'TENAGA',
    name: 'Tenaga Nasional',
    price: 'RM 14.20',
    changePct: -0.28,
    warrantCount: 10,
    callCount: 5,
    putCount: 5,
  },
  {
    ticker: 'PCHEM',
    name: 'Petronas Chem',
    price: 'RM 5.60',
    changePct: 0.0,
    warrantCount: 10,
    callCount: 5,
    putCount: 5,
  },
  {
    ticker: 'INARI',
    name: 'Inari Amertron',
    price: 'RM 3.15',
    changePct: 2.27,
    warrantCount: 10,
    callCount: 6,
    putCount: 4,
  },
  {
    ticker: 'YTL',
    name: 'YTL Corporation',
    price: 'RM 2.85',
    changePct: 3.26,
    warrantCount: 8,
    callCount: 5,
    putCount: 3,
  },
];

export interface MarketTickerRibbonProps {
  activeTicker: string;
  onSelectTicker: (ticker: string) => void;
  className?: string;
}

export const MarketTickerRibbon: React.FC<MarketTickerRibbonProps> = ({
  activeTicker,
  onSelectTicker,
  className,
}) => {
  return (
    <div
      className={cn(
        'w-full bg-card border-2 border-border rounded-xl p-3 shadow-xs',
        className
      )}
    >
      <div className="flex items-center justify-between gap-2 mb-2 px-1">
        <div className="flex items-center gap-2">
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-1.5">
            <Zap className="h-3.5 w-3.5 text-amber-500 fill-amber-500" />
            Live Bursa Malaysia Underlyings
          </span>
          <span className="text-[11px] text-muted-foreground font-semibold hidden sm:inline">
            • Click any stock to load its warrant universe & cards
          </span>
        </div>
        <span className="text-[11px] font-mono font-bold text-indigo-700 dark:text-indigo-400">
          {BURSA_UNDERLYINGS.reduce((sum, item) => sum + item.warrantCount, 0)} Active Warrants
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {BURSA_UNDERLYINGS.map((item) => {
          const isActive = item.ticker === activeTicker;
          const isUp = item.changePct > 0;
          const isDown = item.changePct < 0;

          return (
            <button
              key={item.ticker}
              type="button"
              onClick={() => onSelectTicker(item.ticker)}
              className={cn(
                'flex flex-col justify-between text-left p-2.5 rounded-lg border-2 transition-all duration-150 relative overflow-hidden group',
                isActive
                  ? 'border-indigo-600 bg-indigo-50/90 dark:bg-indigo-950/60 shadow-xs'
                  : 'border-border bg-card hover:border-foreground/80 hover:bg-muted/40'
              )}
            >
              {isActive && (
                <div className="absolute top-0 right-0 h-2 w-2 bg-indigo-500 rounded-bl-sm" />
              )}
              <div className="flex items-center justify-between w-full">
                <span className="font-mono font-bold text-xs text-foreground group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                  {item.ticker}
                </span>
                <span
                  className={cn(
                    'inline-flex items-center gap-0.5 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded-sm',
                    isUp
                      ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-500/10'
                      : isDown
                      ? 'text-rose-700 dark:text-rose-400 bg-rose-500/10'
                      : 'text-muted-foreground bg-muted'
                  )}
                >
                  {isUp && <TrendingUp className="h-2.5 w-2.5" />}
                  {isDown && <TrendingDown className="h-2.5 w-2.5" />}
                  {isUp ? `+${item.changePct.toFixed(2)}%` : `${item.changePct.toFixed(2)}%`}
                </span>
              </div>

              <div className="mt-1 flex items-baseline justify-between w-full">
                <span className="text-xs font-semibold text-foreground font-mono">
                  {item.price}
                </span>
                <span className="text-[10px] text-muted-foreground font-mono flex items-center gap-1">
                  <Layers className="h-2.5 w-2.5 opacity-60" />
                  <span className="text-emerald-600 font-semibold">{item.callCount}C</span>/
                  <span className="text-purple-600 font-semibold">{item.putCount}P</span>
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
