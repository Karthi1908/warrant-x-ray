/**
 * Client-side formatting helpers mirroring server-side deterministic formats.
 */

export function formatCurrency(
  val?: number | null,
  decimals?: number,
  prefix: string = 'RM '
): string {
  if (val === undefined || val === null || isNaN(val)) return '—';
  const dec = decimals !== undefined ? decimals : Math.abs(val) < 1.0 ? 3 : 2;
  return `${prefix}${val.toFixed(dec)}`;
}

export function formatPercent(
  val?: number | null,
  decimals: number = 1,
  signed: boolean = false
): string {
  if (val === undefined || val === null || isNaN(val)) return '—';
  const pct = val * 100.0;
  if (signed && pct > 0) {
    return `+${pct.toFixed(decimals)}%`;
  }
  return `${pct.toFixed(decimals)}%`;
}

export function formatPoints(
  val?: number | null,
  decimals: number = 1,
  signed: boolean = true
): string {
  if (val === undefined || val === null || isNaN(val)) return '—';
  if (signed && val > 0) {
    return `+${val.toFixed(decimals)} pts`;
  }
  return `${val.toFixed(decimals)} pts`;
}

export function formatRatio(val?: number | null, decimals: number = 2): string {
  if (val === undefined || val === null || isNaN(val)) return '—';
  return `${val.toFixed(decimals)}x`;
}

export function formatGreek(val?: number | null, decimals: number = 3): string {
  if (val === undefined || val === null || isNaN(val)) return '—';
  return val.toFixed(decimals);
}

export function formatInt(val?: number | null): string {
  if (val === undefined || val === null || isNaN(val)) return '—';
  return Math.round(val).toLocaleString();
}

export function formatDays(val?: number | null): string {
  if (val === undefined || val === null || isNaN(val)) return '—';
  const ival = Math.round(val);
  return ival === 1 ? '1 day' : `${ival} days`;
}
