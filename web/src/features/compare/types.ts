export interface ComparedWarrantItem {
  code: string;
  issuer: string;
  type: string;
  underlying_ticker: string;
  underlying_price?: number | null;
  display_underlying_price?: string | null;
  strike: number;
  display_strike: string;
  ratio: number;
  display_ratio: string;
  expiry_date: string;
  days_to_expiry?: number | null;
  display_days_to_expiry?: string | null;
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
  spread_cost?: number | null;
  display_spread_cost?: string | null;
  flat_decay?: number | null;
  display_flat_decay?: string | null;
  iv_crush?: number | null;
  display_iv_crush?: string | null;
  breakeven_move?: number | null;
  display_breakeven_move?: string | null;
  flags: Array<{
    code: string;
    severity: string;
    threshold: string | number;
    value?: string | number | null;
    text: string;
  }>;
}

export interface WarrantComparisonResult {
  underlying_ticker: string;
  holding_days: number;
  comparison: ComparedWarrantItem[];
  as_of?: string;
  mode?: string;
  evidence_id?: string;
}
