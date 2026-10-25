/**
 * Educational glossary tooltips for warrant metrics and Greeks.
 */

export interface GlossaryEntry {
  term: string;
  definition: string;
  formula?: string;
}

export const GLOSSARY: Record<string, GlossaryEntry> = {
  effective_gearing: {
    term: 'Effective Gearing',
    definition:
      'The percentage move in the warrant price for a 1% move in the underlying stock price. Takes delta into account.',
    formula: 'Gearing × |Delta|',
  },
  implied_volatility: {
    term: 'Implied Volatility (IV)',
    definition:
      'The annualized expected volatility of the underlying stock priced into the warrant quotes via the Black-Scholes model.',
  },
  theta_decay: {
    term: 'Theta (Time Decay)',
    definition:
      'The estimated daily loss of warrant value due solely to the passage of time, holding stock price and volatility constant.',
  },
  spread_cost: {
    term: 'Spread Cost',
    definition:
      'The percentage loss incurred immediately upon crossing the market maker bid-ask spread to enter and exit.',
    formula: '(Ask - Bid) / Mid',
  },
  moneyness: {
    term: 'Moneyness',
    definition:
      'Position of the underlying price relative to the strike price. Above 1.0 is In-The-Money for Calls; below 1.0 is Out-of-The-Money.',
    formula: 'Stock Price / Strike Price (Calls)',
  },
  breakeven: {
    term: 'Breakeven Price',
    definition:
      'The underlying stock price required at warrant expiry to recoup the entry premium paid.',
    formula: 'Strike + (Ask × Ratio)',
  },
  ratio: {
    term: 'Entitlement Ratio',
    definition:
      'The number of warrants needed to control or exercise into one share of the underlying stock.',
  },
  delta: {
    term: 'Delta',
    definition:
      'The change in warrant price for a RM 1.00 move in the underlying stock price.',
  },
  gamma: {
    term: 'Gamma',
    definition:
      'The rate of change in Delta for a RM 1.00 move in the underlying stock price.',
  },
  vega: {
    term: 'Vega per Point',
    definition:
      'The change in warrant price for a 1 percentage point (+1 pt) shift in implied volatility.',
  },
};

export function getGlossaryTerm(key: string): GlossaryEntry | undefined {
  return GLOSSARY[key];
}

