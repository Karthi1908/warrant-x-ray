import { describe, it, expect } from 'vitest';
import {
  formatCurrency,
  formatPercent,
  formatPoints,
  formatRatio,
  formatGreek,
  formatDays,
  formatInt,
} from '../src/lib/format';
import { hasProhibitedRecommendationCopy, PROHIBITED_WORDS } from '../src/lib/copy';
import { GLOSSARY } from '../src/lib/glossary';

describe('Shared Formatting and Copy', () => {
  it('formats currency correctly (3 decimals for <1, 2 decimals for >=1)', () => {
    expect(formatCurrency(0.085)).toBe('RM 0.085');
    expect(formatCurrency(10.5)).toBe('RM 10.50');
    expect(formatCurrency(null)).toBe('—');
  });

  it('formats percentages and signed moves', () => {
    expect(formatPercent(0.052)).toBe('5.2%');
    expect(formatPercent(0.052, 1, true)).toBe('+5.2%');
    expect(formatPercent(-0.035, 1, true)).toBe('-3.5%');
    expect(formatPercent(null)).toBe('—');
  });

  it('formats ratio, greeks, points and integers', () => {
    expect(formatRatio(4.5)).toBe('4.50x');
    expect(formatGreek(0.523)).toBe('0.523');
    expect(formatDays(5)).toBe('5 days');
    expect(formatDays(1)).toBe('1 day');
    expect(formatPoints(2.5)).toBe('+2.5 pts');
    expect(formatPoints(-1.0)).toBe('-1.0 pts');
    expect(formatInt(1250)).toBe('1,250');
  });

  it('detects prohibited recommendation copy and validates word list', () => {
    expect(PROHIBITED_WORDS.length).toBeGreaterThan(0);
    expect(hasProhibitedRecommendationCopy('You should buy this warrant')).toBe(true);
    expect(hasProhibitedRecommendationCopy('Strong buy recommendation')).toBe(true);
    expect(hasProhibitedRecommendationCopy('Sila beli waran ini')).toBe(true);
    expect(hasProhibitedRecommendationCopy('Factual warrant metrics and Greeks analysis')).toBe(
      false
    );
  });

  it('verifies glossary entries exist for key metrics', () => {
    expect(GLOSSARY.effective_gearing).toBeDefined();
    expect(GLOSSARY.implied_volatility).toBeDefined();
    expect(GLOSSARY.theta_decay).toBeDefined();
    expect(GLOSSARY.spread_cost).toBeDefined();
  });
});
