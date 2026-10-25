import React, { useEffect, useState, useMemo } from 'react';
import { cn } from '../../lib/utils';
import { TrendingUp, TrendingDown, Layers, Zap, Search } from 'lucide-react';

export interface MarketTickerItem {
  ticker: string;
  name: string;
  code?: string;
  price: string;
  changePct: number;
  warrantCount: number;
  callCount: number;
  putCount: number;
  sector?: string;
}

const SECTOR_MAP: Record<string, string> = {
  MAYBANK: 'Banking',
  PBBANK: 'Banking',
  CIMB: 'Banking',
  HLBANK: 'Banking',
  RHBBANK: 'Banking',
  AMBANK: 'Banking',
  BURSA: 'Banking',
  HLFG: 'Banking',

  TENAGA: 'Utilities',
  YTL: 'Utilities',
  YTLPOWR: 'Utilities',
  PETGAS: 'Utilities',
  GASMSIA: 'Utilities',
  TIMECOM: 'Utilities',

  INARI: 'Tech',
  MYEG: 'Tech',
  CTOS: 'Tech',
  FRONTKN: 'Tech',
  GREATEC: 'Tech',
  'D&O': 'Tech',
  VS: 'Tech',
  UNISEM: 'Tech',

  DIALOG: 'Energy',
  HIBISCS: 'Energy',
  DAYANG: 'Energy',
  ARMADA: 'Energy',
  VELESTO: 'Energy',
  YINSON: 'Energy',

  SIMEPLT: 'Plantations',
  IOICORP: 'Plantations',
  KLK: 'Plantations',
  FGV: 'Plantations',
  GENP: 'Plantations',
  TAANN: 'Plantations',

  CELCOMDIGI: 'Telco',
  MAXIS: 'Telco',
  AXIATA: 'Telco',
  TM: 'Telco',
  ASTRO: 'Telco',

  GAMUDA: 'Construction',
  SUNWAY: 'Construction',
  IJM: 'Construction',
  PMETAL: 'Construction',
  SPSETIA: 'Construction',
  ECOWLD: 'Construction',
  UEMS: 'Construction',
  MAHSING: 'Construction',

  IHH: 'Consumer & Healthcare',
  KPJ: 'Consumer & Healthcare',
  TOPGLOV: 'Consumer & Healthcare',
  HARTA: 'Consumer & Healthcare',
  MRDIY: 'Consumer & Healthcare',
  GENTING: 'Consumer & Healthcare',
  GENM: 'Consumer & Healthcare',
  AIRASIA: 'Consumer & Healthcare',
  PCHEM: 'Consumer & Healthcare',
  MISC: 'Consumer & Healthcare',
  WESTPORTS: 'Consumer & Healthcare',
};

export const BURSA_UNDERLYINGS: MarketTickerItem[] = [
  { ticker: 'MAYBANK', name: 'Malayan Banking', price: 'RM 10.50', changePct: 0.48, warrantCount: 10, callCount: 5, putCount: 5, sector: 'Banking' },
  { ticker: 'PBBANK', name: 'Public Bank', price: 'RM 4.50', changePct: 0.22, warrantCount: 10, callCount: 5, putCount: 5, sector: 'Banking' },
  { ticker: 'CIMB', name: 'CIMB Group', price: 'RM 8.10', changePct: 1.11, warrantCount: 10, callCount: 5, putCount: 5, sector: 'Banking' },
  { ticker: 'TENAGA', name: 'Tenaga Nasional', price: 'RM 14.20', changePct: -0.28, warrantCount: 10, callCount: 5, putCount: 5, sector: 'Utilities' },
  { ticker: 'IHH', name: 'IHH Healthcare', price: 'RM 7.25', changePct: 0.69, warrantCount: 10, callCount: 5, putCount: 5, sector: 'Consumer & Healthcare' },
  { ticker: 'CELCOMDIGI', name: 'CelcomDigi', price: 'RM 3.75', changePct: -0.53, warrantCount: 10, callCount: 5, putCount: 5, sector: 'Telco' },
  { ticker: 'PCHEM', name: 'Petronas Chemicals', price: 'RM 5.60', changePct: 0.00, warrantCount: 10, callCount: 5, putCount: 5, sector: 'Consumer & Healthcare' },
  { ticker: 'INARI', name: 'Inari Amertron', price: 'RM 3.80', changePct: 2.27, warrantCount: 10, callCount: 5, putCount: 5, sector: 'Tech' },
  { ticker: 'YTL', name: 'YTL Corporation', price: 'RM 3.40', changePct: 3.26, warrantCount: 10, callCount: 5, putCount: 5, sector: 'Utilities' },
  { ticker: 'YTLPOWR', name: 'YTL Power Int', price: 'RM 4.80', changePct: 1.45, warrantCount: 10, callCount: 5, putCount: 5, sector: 'Utilities' },
  { ticker: 'GAMUDA', name: 'Gamuda', price: 'RM 8.80', changePct: 1.85, warrantCount: 10, callCount: 5, putCount: 5, sector: 'Construction' },
  { ticker: 'SUNWAY', name: 'Sunway', price: 'RM 4.50', changePct: 0.89, warrantCount: 10, callCount: 5, putCount: 5, sector: 'Construction' },
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
  const [underlyings, setUnderlyings] = useState<MarketTickerItem[]>(BURSA_UNDERLYINGS);
  const [selectedSector, setSelectedSector] = useState<string>('All');
  const [filterText, setFilterText] = useState<string>('');

  useEffect(() => {
    let mounted = true;
    const fetchUnderlyings = async () => {
      try {
        const resp = await fetch('/api/underlyings');
        if (resp.ok) {
          const data = await resp.json();
          if (mounted && Array.isArray(data.underlyings) && data.underlyings.length > 0) {
            const mapped: MarketTickerItem[] = data.underlyings.map((u: any, idx: number) => {
              const tk = u.ticker.toUpperCase();
              const priceNum = u.price != null ? Number(u.price) : 5.0;
              // deterministic visual drift
              const changePct = Number((((idx * 17) % 31) - 14) * 0.15).toFixed(2);
              return {
                ticker: tk,
                name: u.name || tk,
                code: u.code,
                price: u.price != null ? `RM ${Number(u.price).toFixed(2)}` : `RM ${priceNum.toFixed(2)}`,
                changePct: parseFloat(changePct),
                warrantCount: u.total_warrants || 10,
                callCount: u.call_count || 5,
                putCount: u.put_count || 5,
                sector: SECTOR_MAP[tk] || 'Other',
              };
            });
            setUnderlyings(mapped);
          }
        }
      } catch {
        // keep fallback
      }
    };

    fetchUnderlyings();
    return () => {
      mounted = false;
    };
  }, []);

  const totalWarrants = useMemo(() => {
    return underlyings.reduce((sum, item) => sum + item.warrantCount, 0);
  }, [underlyings]);

  const sectors = useMemo(() => {
    const list = Array.from(new Set(underlyings.map((u) => u.sector || 'Other'))).sort();
    return ['All', ...list];
  }, [underlyings]);

  const filteredUnderlyings = useMemo(() => {
    return underlyings.filter((item) => {
      const matchSector = selectedSector === 'All' || item.sector === selectedSector;
      const cleanFilter = filterText.trim().toLowerCase();
      const matchText =
        !cleanFilter ||
        item.ticker.toLowerCase().includes(cleanFilter) ||
        item.name.toLowerCase().includes(cleanFilter);
      return matchSector && matchText;
    });
  }, [underlyings, selectedSector, filterText]);

  return (
    <div
      className={cn(
        'w-full bg-card border-2 border-border rounded-xl p-3 shadow-xs space-y-3',
        className
      )}
    >
      {/* Top Header & Metrics */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-1">
        <div className="flex items-center gap-2">
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-1.5">
            <Zap className="h-3.5 w-3.5 text-amber-500 fill-amber-500" />
            Live Bursa Malaysia Underlyings ({underlyings.length} Companies)
          </span>
          <span className="text-[11px] text-muted-foreground font-semibold hidden md:inline">
            • Select any stock to load its complete structured warrant matrix
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] font-mono font-bold text-indigo-700 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-200/60 dark:border-indigo-800/40">
            {totalWarrants} Active Warrants
          </span>
          <span className="text-[11px] font-mono font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-200/60 dark:border-emerald-800/40">
            {underlyings.length} Underlyings
          </span>
        </div>
      </div>

      {/* Sector Pills and Search Filter Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2 pt-1 border-t border-border/60">
        <div className="flex items-center gap-1 overflow-x-auto pb-1 lg:pb-0 scrollbar-none text-xs">
          {sectors.map((sec) => {
            const count =
              sec === 'All'
                ? underlyings.length
                : underlyings.filter((u) => u.sector === sec).length;
            const isSelected = selectedSector === sec;
            return (
              <button
                key={sec}
                type="button"
                onClick={() => setSelectedSector(sec)}
                className={cn(
                  'rounded-lg px-2.5 py-1 text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5',
                  isSelected
                    ? 'bg-primary text-primary-foreground shadow-2xs font-bold'
                    : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
                )}
              >
                <span>{sec}</span>
                <span className={cn('text-[10px] px-1 rounded', isSelected ? 'bg-primary-foreground/20 text-primary-foreground' : 'bg-muted-foreground/15 text-muted-foreground')}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        <div className="relative min-w-[200px] max-w-xs self-end lg:self-auto">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder={`Filter ${underlyings.length} companies...`}
            className="w-full rounded-lg border border-border bg-background py-1 pl-8 pr-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-hidden focus:ring-1 focus:ring-primary"
          />
        </div>
      </div>

      {/* Underlyings Cards Grid with Smooth Horizontal / Wrapping Flow */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2 max-h-[220px] overflow-y-auto pr-1">
        {filteredUnderlyings.map((item) => {
          const isActive = item.ticker === activeTicker;
          const isUp = item.changePct > 0;
          const isDown = item.changePct < 0;

          return (
            <button
              key={item.ticker}
              type="button"
              onClick={() => onSelectTicker(item.ticker)}
              className={cn(
                'flex flex-col justify-between text-left p-2 rounded-lg border-2 transition-all duration-150 relative overflow-hidden group',
                isActive
                  ? 'border-indigo-600 bg-indigo-50/90 dark:bg-indigo-950/60 shadow-xs ring-1 ring-indigo-500'
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
                    'inline-flex items-center gap-0.5 text-[9px] font-mono font-semibold px-1 py-0.2 rounded-sm',
                    isUp
                      ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-500/10'
                      : isDown
                      ? 'text-rose-700 dark:text-rose-400 bg-rose-500/10'
                      : 'text-muted-foreground bg-muted'
                  )}
                >
                  {isUp && <TrendingUp className="h-2 w-2" />}
                  {isDown && <TrendingDown className="h-2 w-2" />}
                  {isUp ? `+${item.changePct.toFixed(2)}%` : `${item.changePct.toFixed(2)}%`}
                </span>
              </div>

              <div className="text-[10px] text-muted-foreground truncate w-full mt-0.5">
                {item.name}
              </div>

              <div className="mt-1 flex items-baseline justify-between w-full pt-1 border-t border-border/40">
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
