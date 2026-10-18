import React, { useEffect, useState } from 'react';
import { cn } from '../../lib/utils';
import {
  Activity,
  Radio,
  Clock,
  ShieldCheck,
  Users,
  Eye,
  MessageSquare,
  Cpu,
  RefreshCw,
  CheckCircle2,
} from 'lucide-react';

export interface MetaData {
  version: string;
  mode: string;
  as_of: string;
  market_open: boolean;
  stale: boolean;
  staleness_seconds: number;
  last_collection_status: string;
  resolved_model_ids?: Record<string, string>;
  tier_health?: Record<string, string>;
  usage_metrics?: {
    total_visits?: number;
    daily_uniques?: number;
    interactive_queries?: number;
    visits?: number;
    unique_visitors_daily?: number;
  };
}

export const HealthTab: React.FC = () => {
  const [meta, setMeta] = useState<MetaData | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const fetchMeta = async () => {
    setLoading(true);
    try {
      const resp = await fetch('/api/meta');
      if (resp.ok) {
        const data = await resp.json();
        setMeta(data);
        setLastRefreshed(new Date());
      }
    } catch {
      // Offline fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMeta();
    const interval = setInterval(fetchMeta, 30000); // 30s auto-refresh
    return () => clearInterval(interval);
  }, []);

  const totalVisits = meta?.usage_metrics?.total_visits ?? meta?.usage_metrics?.visits ?? 0;
  const dailyUniques =
    meta?.usage_metrics?.daily_uniques ?? meta?.usage_metrics?.unique_visitors_daily ?? 0;
  const interactiveQueries = meta?.usage_metrics?.interactive_queries ?? 0;

  const stalenessMinutes = meta?.staleness_seconds ? Math.floor(meta.staleness_seconds / 60) : 0;

  return (
    <div className="space-y-6">
      {/* Tab Header & Refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold tracking-tight text-foreground flex items-center space-x-2">
            <Activity className="h-4 w-4 text-primary" />
            <span>System Health & Operational Status</span>
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time Bursa Malaysia data freshness, collector status, and public usage metrics (FR-020).
          </p>
        </div>

        <button
          type="button"
          onClick={fetchMeta}
          disabled={loading}
          className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg border border-border bg-card/60 hover:bg-muted text-xs font-medium text-foreground transition-all shadow-sm"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin text-primary')} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Grid of Key Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Market Session & Mode */}
        <div className="rounded-xl border border-border/70 bg-card/50 p-4 space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium flex items-center space-x-1.5">
              <Radio className="h-3.5 w-3.5 text-primary" />
              <span>Session & Mode</span>
            </span>
            <span className="font-mono text-[11px] uppercase tracking-wide px-2 py-0.5 rounded bg-muted">
              {meta?.mode ?? 'sample'}
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Bursa Market Status:</span>
              <span
                className={cn(
                  'text-xs font-medium px-2 py-0.5 rounded-full inline-flex items-center space-x-1',
                  meta?.market_open
                    ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                    : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                )}
              >
                <span
                  className={cn(
                    'h-1.5 w-1.5 rounded-full',
                    meta?.market_open ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
                  )}
                />
                <span>{meta?.market_open ? 'Trading Open' : 'Market Closed'}</span>
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Trading Hours:</span>
              <span className="text-xs font-mono text-foreground">09:00-12:30, 14:30-17:00 MYT</span>
            </div>
          </div>
        </div>

        {/* Data Staleness */}
        <div className="rounded-xl border border-border/70 bg-card/50 p-4 space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium flex items-center space-x-1.5">
              <Clock className="h-3.5 w-3.5 text-amber-500" />
              <span>Data Freshness</span>
            </span>
            <span
              className={cn(
                'text-[11px] font-medium px-2 py-0.5 rounded-full inline-flex items-center space-x-1',
                meta?.stale
                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                  : 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
              )}
            >
              <span>{meta?.stale ? 'Stale (>20m)' : 'Fresh'}</span>
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Market As-Of:</span>
              <span className="text-xs font-mono text-foreground truncate max-w-[150px]" title={meta?.as_of}>
                {meta?.as_of ? new Date(meta.as_of).toLocaleTimeString() : 'N/A'}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Elapsed Age:</span>
              <span className="text-xs font-mono text-foreground">
                {stalenessMinutes} min ({meta?.staleness_seconds ?? 0}s)
              </span>
            </div>
          </div>
        </div>

        {/* Collector Health */}
        <div className="rounded-xl border border-border/70 bg-card/50 p-4 space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium flex items-center space-x-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
              <span>Collector Health</span>
            </span>
            <span className="text-[11px] font-medium text-emerald-500 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full inline-flex items-center space-x-1">
              <CheckCircle2 className="h-3 w-3" />
              <span>{meta?.last_collection_status ?? 'ok'}</span>
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Pacing & Interval:</span>
              <span className="font-mono text-foreground">5.0s min interval</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">User-Agent:</span>
              <span className="font-mono text-foreground text-[11px]">WarrantXRay/1.0</span>
            </div>
          </div>
        </div>
      </div>

      {/* Public Usage Metrics (FR-020) */}
      <div className="rounded-xl border border-border/70 bg-card/50 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center space-x-1.5">
              <Users className="h-3.5 w-3.5 text-primary" />
              <span>Public Usage Metrics (FR-020)</span>
            </h3>
            <p className="text-xs text-muted-foreground">
              Transparent, anonymous counters salted daily. Raw IP addresses are never logged or stored.
            </p>
          </div>
          <span className="text-[11px] text-muted-foreground font-mono">
            Updated: {lastRefreshed.toLocaleTimeString()}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
          <div className="p-3.5 rounded-lg border border-border/60 bg-muted/20 space-y-1">
            <div className="flex items-center space-x-2 text-xs text-muted-foreground">
              <Eye className="h-3.5 w-3.5 text-blue-400" />
              <span>Total Visits</span>
            </div>
            <div className="text-2xl font-bold font-mono tracking-tight text-foreground">
              {totalVisits.toLocaleString()}
            </div>
          </div>

          <div className="p-3.5 rounded-lg border border-border/60 bg-muted/20 space-y-1">
            <div className="flex items-center space-x-2 text-xs text-muted-foreground">
              <Users className="h-3.5 w-3.5 text-emerald-400" />
              <span>Daily Uniques</span>
            </div>
            <div className="text-2xl font-bold font-mono tracking-tight text-foreground">
              {dailyUniques.toLocaleString()}
            </div>
          </div>

          <div className="p-3.5 rounded-lg border border-border/60 bg-muted/20 space-y-1">
            <div className="flex items-center space-x-2 text-xs text-muted-foreground">
              <MessageSquare className="h-3.5 w-3.5 text-purple-400" />
              <span>Interactive Queries</span>
            </div>
            <div className="text-2xl font-bold font-mono tracking-tight text-foreground">
              {interactiveQueries.toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* Model Tier Health */}
      <div className="rounded-xl border border-border/70 bg-card/50 p-5 space-y-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center space-x-1.5">
          <Cpu className="h-3.5 w-3.5 text-primary" />
          <span>LLM Model Routing & Tier Health</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3 rounded-lg border border-border/50 bg-muted/10 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-foreground">Nano Tier</span>
              <span className="text-[10px] font-medium text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                {meta?.tier_health?.nano ?? 'healthy'}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Intent checks, entity extraction, JSON formatting repair.
            </p>
            <div className="font-mono text-[10px] text-muted-foreground truncate">
              {meta?.resolved_model_ids?.nano ?? 'nvidia/nemotron-mini-4b-instruct'}
            </div>
          </div>

          <div className="p-3 rounded-lg border border-border/50 bg-muted/10 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-foreground">Super Tier (Primary)</span>
              <span className="text-[10px] font-medium text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                {meta?.tier_health?.super ?? 'healthy'}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Multi-step tool calling, warrant card explanations, holding risk.
            </p>
            <div className="font-mono text-[10px] text-muted-foreground truncate">
              {meta?.resolved_model_ids?.super ?? 'nvidia/nemotron-4-70b-instruct'}
            </div>
          </div>

          <div className="p-3 rounded-lg border border-border/50 bg-muted/10 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-foreground">Ultra Tier (Cross-Check)</span>
              <span className="text-[10px] font-medium text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                {meta?.tier_health?.ultra ?? 'healthy'}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Deep research, cross-checks, edge case ambiguity resolution.
            </p>
            <div className="font-mono text-[10px] text-muted-foreground truncate">
              {meta?.resolved_model_ids?.ultra ?? 'nvidia/nemotron-4-340b-instruct'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
