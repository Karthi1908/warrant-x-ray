/**
 * Card feature type definitions.
 * Matches backend WarrantCard and API schemas.
 */

export interface FlagItemData {
  code: string;
  severity: 'warn' | 'high' | string;
  threshold: string | number;
  value?: string | number | null;
  text: string;
}

export interface NotEvaluatedItemData {
  flag: string;
  reason: string;
}

export interface HoldingCostPresetsData {
  spread_cost?: number | null;
  display_spread_cost?: string | null;
  flat_decay?: number | null;
  display_flat_decay?: string | null;
  iv_crush?: number | null;
  display_iv_crush?: string | null;
  gearing_check?: number | null;
  display_gearing_check?: string | null;
  breakeven_move?: number | null;
  display_breakeven_move?: string | null;
}

export interface WarrantMetricsData {
  shares_per_warrant?: number | null;
  display_shares_per_warrant?: string | null;
  days_to_expiry?: number | null;
  display_days_to_expiry?: string | null;
  mid?: number | null;
  display_mid?: string | null;
  size_weighted_mid?: number | null;
  display_size_weighted_mid?: string | null;
  spread_pct?: number | null;
  display_spread_pct?: string | null;
  round_trip_cost?: number | null;
  display_round_trip_cost?: string | null;
  headline_iv?: number | null;
  display_headline_iv?: string | null;
  headline_iv_basis?: string;
  iv_by_basis?: Record<string, number | null>;
  iv_reason_codes?: Record<string, string | null>;
  iv_basis_spread?: number | null;
  display_iv_basis_spread?: string | null;
  delta_share?: number | null;
  display_delta_share?: string | null;
  gamma?: number | null;
  display_gamma?: string | null;
  vega_per_point?: number | null;
  display_vega_per_point?: string | null;
  theta_per_day?: number | null;
  display_theta_per_day?: string | null;
  gearing?: number | null;
  display_gearing?: string | null;
  effective_gearing?: number | null;
  display_effective_gearing?: string | null;
  premium?: number | null;
  display_premium?: string | null;
  breakeven_price?: number | null;
  display_breakeven_price?: string | null;
  required_move?: number | null;
  display_required_move?: string | null;
  cross_check?: {
    iv_diff_points?: number | null;
    eg_diff_rel?: number | null;
    delta_diff?: number | null;
    [key: string]: number | null | undefined;
  } | null;
}

export interface WarrantCardData {
  code: string;
  issuer: string;
  type: string;
  underlying_ticker: string;
  expiry_date: string;
  strike: number;
  display_strike: string;
  ratio_raw: number;
  display_ratio: string;
  underlying_price?: number | null;
  display_underlying_price?: string | null;
  bid?: number | null;
  display_bid?: string | null;
  ask?: number | null;
  display_ask?: string | null;
  metrics: WarrantMetricsData;
  holding_days: number;
  presets: HoldingCostPresetsData;
  flags: FlagItemData[];
  not_evaluated: NotEvaluatedItemData[];
  evidence_id?: string;
  as_of?: string;
  mode?: string;
  expired?: boolean;
}
