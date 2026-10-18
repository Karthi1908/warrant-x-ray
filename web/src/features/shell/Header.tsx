import React, { useState, useEffect } from 'react';
import { cn } from '../../lib/utils';
import { DataBadge, type DataMode } from './DataBadge';
import { SnapshotPicker } from './SnapshotPicker';
import { Activity, Sun, Moon, Sparkles } from 'lucide-react';

export interface HeaderProps {
  mode?: DataMode;
  asOf?: string;
  isStale?: boolean;
  marketOpen?: boolean;
  selectedSnapshotId?: number | null;
  onSelectSnapshot?: (id: number | null) => void;
  className?: string;
}

export const Header: React.FC<HeaderProps> = ({
  mode = 'replay',
  asOf,
  isStale = false,
  marketOpen = false,
  selectedSnapshotId,
  onSelectSnapshot,
  className,
}) => {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains('dark'));
  }, []);

  const toggleTheme = () => {
    if (document.documentElement.classList.contains('dark')) {
      document.documentElement.classList.remove('dark');
      setIsDark(false);
    } else {
      document.documentElement.classList.add('dark');
      setIsDark(true);
    }
  };

  return (
    <header
      className={cn(
        'border-b border-border/80 bg-card/90 backdrop-blur-md px-4 sm:px-6 py-3 flex items-center justify-between sticky top-0 z-30 shadow-xs',
        className
      )}
    >
      <div className="flex items-center space-x-3">
        <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-blue-500 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-500/25 ring-2 ring-indigo-400/20">
          <Activity className="h-5 w-5" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-base sm:text-lg font-extrabold tracking-tight bg-gradient-to-r from-indigo-700 via-indigo-600 to-blue-600 dark:from-indigo-400 dark:to-blue-400 bg-clip-text text-transparent">
              Warrant X-Ray
            </h1>
            <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/20">
              v0.1
            </span>
            <span className="hidden md:inline-flex items-center gap-1 text-[10px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800/50 rounded-full px-2 py-0.5">
              <Sparkles className="h-2.5 w-2.5" /> Bursa Copilot
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground font-medium">
            Bursa Malaysia Structured Warrants • Deterministic Quant & Risk Engine
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-2 sm:space-x-3">
        <SnapshotPicker
          selectedSnapshotId={selectedSnapshotId}
          onSelectSnapshot={onSelectSnapshot}
        />
        <DataBadge mode={mode} asOf={asOf} isStale={isStale} marketOpen={marketOpen} />

        {/* Theme Toggle Button */}
        <button
          type="button"
          onClick={toggleTheme}
          title={isDark ? 'Switch to Vibrant Light Mode' : 'Switch to Dark Mode'}
          className="p-2 rounded-xl border border-border bg-card hover:bg-muted text-muted-foreground hover:text-foreground transition-all shadow-xs"
        >
          {isDark ? (
            <Sun className="h-4 w-4 text-amber-500" />
          ) : (
            <Moon className="h-4 w-4 text-indigo-600" />
          )}
        </button>
      </div>
    </header>
  );
};
