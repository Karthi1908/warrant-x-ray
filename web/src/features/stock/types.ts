export interface NearestWarrant {
  code: string;
  type: string;
  strike: number;
  display_strike: string;
  distance_from_strike: number;
  display_distance_from_strike: string;
  bid?: number | null;
  display_bid?: string | null;
  ask?: number | null;
  display_ask?: string | null;
  days_to_expiry?: number | null;
  display_days_to_expiry?: string | null;
  effective_gearing?: number | null;
  display_effective_gearing?: string | null;
}

export interface StockSummary {
  ticker: string;
  as_of: string;
  underlying_price?: number | null;
  display_underlying_price?: string | null;
  call_count: number;
  put_count: number;
  issuer_count: number;
  issuers: string[];
  min_expiry?: string | null;
  max_expiry?: string | null;
  median_spread_pct?: number | null;
  display_median_spread_pct?: string | null;
  median_flat_decay?: number | null;
  display_median_flat_decay?: string | null;
  flag_counts: Record<string, number>;
  nearest_warrants: NearestWarrant[];
  volatility_10d?: number | null;
  display_volatility_10d?: string | null;
  volatility_30d?: number | null;
  display_volatility_30d?: string | null;
  evidence_id: string;
}

export interface WarrantListItem {
  code: string;
  issuer: string;
  type: string;
  underlying_ticker: string;
  expiry_date: string;
  strike: number;
  display_strike: string;
  ratio_raw: number;
  display_ratio: string;
  bid?: number | null;
  display_bid?: string | null;
  ask?: number | null;
  display_ask?: string | null;
  mid?: number | null;
  display_mid?: string | null;
  spread_pct?: number | null;
  display_spread_pct?: string | null;
  effective_gearing?: number | null;
  display_effective_gearing?: string | null;
  headline_iv?: number | null;
  display_headline_iv?: string | null;
  headline_iv_basis?: string;
  days_to_expiry?: number | null;
  display_days_to_expiry?: string | null;
  flags_count?: number;
}

export interface WarrantSearchResponse {
  results: WarrantListItem[];
  total: number;
  count: number;
  iv_basis: string;
  as_of?: string;
  message?: string;
}

export interface UnderlyingItem {
  ticker: string;
  warrant_count: number;
}
