import React from 'react';
import { cn } from '../../lib/utils';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  Legend,
} from 'recharts';

export interface CurvePointData {
  move: number;
  display_move: string;
  pnl_pct?: number | null;
  display_pnl_pct?: string | null;
}

export interface ScenarioCurveData {
  horizon_days: number;
  display_horizon: string;
  points: CurvePointData[];
}

export interface PnlChartProps {
  curves: ScenarioCurveData[];
  breakevenMove?: number | null;
  displayBreakeven?: string | null;
  currentMove?: number;
  currentPnl?: number;
  className?: string;
}

const HORIZON_COLORS = ['#3b82f6', '#10b981', '#a855f7'];

export const PnlChart: React.FC<PnlChartProps> = ({
  curves,
  breakevenMove,
  displayBreakeven,
  currentMove: _currentMove,
  currentPnl: _currentPnl,
  className,
}) => {
  if (!curves || curves.length === 0) {
    return (
      <div className={cn('flex items-center justify-center p-8 text-xs text-muted-foreground', className)}>
        No curve data available.
      </div>
    );
  }

  // Merge points into a unified table format for Recharts
  // x: move percentage, e.g. -20% to +20%
  const moveMap = new Map<number, Record<string, number | string>>();

  curves.forEach((curve) => {
    const key = `h_${curve.horizon_days}`;
    curve.points.forEach((pt) => {
      const moveKey = Math.round(pt.move * 100);
      if (!moveMap.has(moveKey)) {
        moveMap.set(moveKey, {
          movePct: moveKey,
          label: `${moveKey > 0 ? '+' : ''}${moveKey}%`,
        });
      }
      const entry = moveMap.get(moveKey)!;
      if (pt.pnl_pct != null) {
        entry[key] = Math.round(pt.pnl_pct * 1000) / 10; // e.g. 15.5%
      }
    });
  });

  const chartData = Array.from(moveMap.values()).sort(
    (a, b) => (a.movePct as number) - (b.movePct as number)
  );

  return (
    <div className={cn('rounded-xl border border-border bg-card p-4 shadow-sm space-y-3', className)}>
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Warrant P&L Trajectory
          </h4>
          <p className="text-[11px] text-muted-foreground">
            Expected payoff across underlying move horizons
          </p>
        </div>

        {displayBreakeven && (
          <div className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
            Breakeven: {displayBreakeven}
          </div>
        )}
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <XAxis
              dataKey="label"
              stroke="#888888"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#888888"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              formatter={(value: any, name: string) => {
                const curve = curves.find((c) => `h_${c.horizon_days}` === name);
                const label = curve ? curve.display_horizon : name;
                return [`${value}%`, label];
              }}
              labelFormatter={(label) => `Stock Move: ${label}`}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                borderColor: 'hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '12px',
              }}
            />
            <ReferenceLine y={0} stroke="#64748b" strokeDasharray="3 3" />
            {breakevenMove != null && (
              <ReferenceLine
                x={`${Math.round(breakevenMove * 100) > 0 ? '+' : ''}${Math.round(breakevenMove * 100)}%`}
                stroke="#10b981"
                strokeDasharray="4 4"
              />
            )}

            {curves.map((curve, idx) => (
              <Line
                key={curve.horizon_days}
                type="monotone"
                dataKey={`h_${curve.horizon_days}`}
                name={curve.display_horizon}
                stroke={HORIZON_COLORS[idx % HORIZON_COLORS.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
            <Legend
              wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Accessible Horizon Badges */}
      <div className="flex flex-wrap items-center gap-3 pt-1 border-t border-border/40 text-xs">
        {curves.map((curve, idx) => (
          <div key={curve.horizon_days} className="flex items-center space-x-1.5 font-medium">
            <span
              className="h-2.5 w-2.5 rounded-full shrink-0"
              style={{ backgroundColor: HORIZON_COLORS[idx % HORIZON_COLORS.length] }}
            />
            <span className="text-foreground/80">{curve.display_horizon}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
