/**
 * Static UX copy and compliance rules.
 * Strictly prohibits financial recommendations, buy/sell directives, and price targets.
 */

export const PROHIBITED_WORDS = [
  'buy',
  'sell',
  'target price',
  'undervalued',
  'overvalued',
  'top pick',
  'must buy',
  'strong buy',
  'good investment',
  'beli',
  'jual',
  'untung besar',
];

export function hasProhibitedRecommendationCopy(text: string): boolean {
  const lower = text.toLowerCase();
  return PROHIBITED_WORDS.some((word) => {
    const regex = new RegExp(`\\b${word}\\b`, 'i');
    return regex.test(lower);
  });
}

export const DISCLAIMER_COPY = {
  en: 'Educational and analytical tool only. Not financial, investment, or trading advice. Structured warrants are high-risk leveraged derivatives that can expire worthless.',
  ms: 'Alat pendidikan dan analitikal sahaja. Bukan nasihat kewangan, pelaburan, atau perdagangan. Waran berstruktur adalah derivatif berleveraj berisiko tinggi yang boleh luput tanpa nilai.',
};

export const PRESET_LABELS = {
  spread_cost: 'Spread cost',
  flat_decay: 'Holding decay',
  iv_crush: 'IV crush (-5 pts)',
  gearing_check: 'Effective gearing',
  breakeven_move: 'Breakeven move',
};
