import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MetricPair } from '../src/features/card/MetricPair';
import { HoldingCostBar } from '../src/features/card/HoldingCostBar';
import { FlagChip } from '../src/features/card/FlagChip';
import { FlagDrawer } from '../src/features/card/FlagDrawer';
import { HoldingDaysStepper } from '../src/features/card/HoldingDaysStepper';
import { CardTab } from '../src/features/card/CardTab';
import type { WarrantCardData } from '../src/features/card/types';

describe('Card Feature Components', () => {
  describe('MetricPair', () => {
    it('renders label, issuer value, and recomputed value', () => {
      render(
        <MetricPair
          label="Effective Gearing"
          issuerValue="5.20x"
          recomputedValue="5.18x"
          diffText="Δ -0.02x"
        />
      );
      expect(screen.getByText('Effective Gearing')).toBeDefined();
      expect(screen.getByText('5.20x')).toBeDefined();
      expect(screen.getByText('5.18x')).toBeDefined();
      expect(screen.getByText('Δ -0.02x')).toBeDefined();
    });

    it('handles null values with em-dash', () => {
      render(
        <MetricPair
          label="Implied Volatility"
          issuerValue={null}
          recomputedValue="45.2%"
        />
      );
      expect(screen.getByText('Implied Volatility')).toBeDefined();
      expect(screen.getByText('—')).toBeDefined();
      expect(screen.getByText('45.2%')).toBeDefined();
    });

    it('highlights significant mismatch with warning badge', () => {
      render(
        <MetricPair
          label="Implied Volatility"
          issuerValue="40.0%"
          recomputedValue="45.0%"
          diff={5.0}
          diffText="Δ +5.0 pts"
          isMismatch={true}
        />
      );
      const diffBadge = screen.getByText('Δ +5.0 pts');
      expect(diffBadge).toBeDefined();
      expect(diffBadge.className).toContain('text-amber');
    });
  });

  describe('HoldingCostBar', () => {
    it('renders spread cost, flat decay, and IV crush', () => {
      const presets = {
        spread_cost: 0.032,
        display_spread_cost: '3.2%',
        flat_decay: 0.018,
        display_flat_decay: '1.8%',
        iv_crush: 0.041,
        display_iv_crush: '4.1%',
        breakeven_move: 0.025,
        display_breakeven_move: '+2.5%',
      };

      render(
        <HoldingCostBar
          presets={presets}
          holdingDays={5}
          underlyingTicker="MAYBANK"
        />
      );

      expect(screen.getByText(/5-day Holding Cost/i)).toBeDefined();
      expect(screen.getByText('3.2%')).toBeDefined();
      expect(screen.getByText('1.8%')).toBeDefined();
      expect(screen.getByText('4.1%')).toBeDefined();
      expect(screen.getByText(/\+2.5%/)).toBeDefined();
    });
  });

  describe('FlagChip', () => {
    it('renders flag code and handles click', () => {
      const onFlagClick = vi.fn();
      const flag = {
        code: 'HIGH_DECAY',
        severity: 'high',
        threshold: '>1.0% per day',
        value: '1.5% per day',
        text: 'Theta decay exceeds 1.0% per day',
      };

      render(<FlagChip flag={flag} onClick={onFlagClick} />);
      const chip = screen.getByText('HIGH_DECAY');
      expect(chip).toBeDefined();

      fireEvent.click(chip);
      expect(onFlagClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('FlagDrawer', () => {
    it('displays triggered flags and not_evaluated flags with reasons', () => {
      const onClose = vi.fn();
      const flags = [
        {
          code: 'SHORT_EXPIRY',
          severity: 'warn',
          threshold: '<14 days',
          value: '10 days',
          text: 'Expires in less than 14 days',
        },
      ];
      const notEvaluated = [
        {
          flag: 'IV_RICH',
          reason: 'Missing 30-day underlying price history to evaluate realized volatility.',
        },
      ];

      render(
        <FlagDrawer
          isOpen={true}
          onClose={onClose}
          flags={flags}
          notEvaluated={notEvaluated}
          warrantCode="MAYBANK-C10"
        />
      );

      expect(screen.getByText(/Risk Flags & Evaluations/i)).toBeDefined();
      expect(screen.getByText('SHORT_EXPIRY')).toBeDefined();
      expect(screen.getByText('Expires in less than 14 days')).toBeDefined();
      expect(screen.getByText('IV_RICH')).toBeDefined();
      expect(
        screen.getByText('Missing 30-day underlying price history to evaluate realized volatility.')
      ).toBeDefined();

      const closeBtn = screen.getByRole('button', { name: /close/i });
      fireEvent.click(closeBtn);
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('HoldingDaysStepper', () => {
    it('increments, decrements, and respects boundaries', () => {
      const onChange = vi.fn();
      render(<HoldingDaysStepper days={5} maxDays={10} onChange={onChange} />);

      const decBtn = screen.getByRole('button', { name: /decrease holding days/i });
      const incBtn = screen.getByRole('button', { name: /increase holding days/i });

      fireEvent.click(decBtn);
      expect(onChange).toHaveBeenCalledWith(4);

      fireEvent.click(incBtn);
      expect(onChange).toHaveBeenCalledWith(6);
    });
  });

  describe('CardTab', () => {
    it('renders full warrant card with header, quotes, and metrics', () => {
      const sampleCard: WarrantCardData = {
        code: '115510',
        issuer: 'CGS',
        type: 'call',
        underlying_ticker: 'MAYBANK',
        expiry_date: '2026-06-30',
        strike: 10.5,
        display_strike: 'RM 10.50',
        ratio_raw: 4.0,
        display_ratio: '4.00x',
        underlying_price: 10.2,
        display_underlying_price: 'RM 10.20',
        bid: 0.15,
        display_bid: 'RM 0.150',
        ask: 0.155,
        display_ask: 'RM 0.155',
        metrics: {
          days_to_expiry: 42,
          display_days_to_expiry: '42 days',
          mid: 0.1525,
          display_mid: 'RM 0.153',
          spread_pct: 0.0328,
          display_spread_pct: '3.3%',
          headline_iv: 0.425,
          display_headline_iv: '42.5%',
          headline_iv_basis: 'mid',
          effective_gearing: 5.2,
          display_effective_gearing: '5.20x',
          delta_share: 0.52,
          display_delta_share: '0.520',
          gamma: 0.12,
          display_gamma: '0.120',
          vega_per_point: 0.0015,
          display_vega_per_point: 'RM 0.0015',
          theta_per_day: -0.002,
          display_theta_per_day: '-RM 0.0020',
          premium: 0.085,
          display_premium: '8.5%',
          breakeven_price: 11.12,
          display_breakeven_price: 'RM 11.12',
          required_move: 0.09,
          display_required_move: '+9.0%',
          cross_check: {
            iv_diff_points: 1.5,
            eg_diff_rel: 0.02,
          },
        },
        holding_days: 5,
        presets: {
          spread_cost: 0.033,
          display_spread_cost: '3.3%',
          flat_decay: 0.02,
          display_flat_decay: '2.0%',
          iv_crush: 0.04,
          display_iv_crush: '4.0%',
          breakeven_move: 0.03,
          display_breakeven_move: '+3.0%',
        },
        flags: [
          {
            code: 'WIDE_SPREAD',
            severity: 'warn',
            threshold: '>3.0%',
            value: '3.3%',
            text: 'Bid-ask spread exceeds 3.0%',
          },
        ],
        not_evaluated: [],
        evidence_id: 'E1',
        as_of: '2026-10-15T09:00:00Z',
        mode: 'replay',
        expired: false,
      };

      render(<CardTab card={sampleCard} onHoldingDaysChange={vi.fn()} />);

      expect(screen.getByText('115510')).toBeDefined();
      expect(screen.getByText('CGS')).toBeDefined();
      expect(screen.getByText('MAYBANK')).toBeDefined();
      expect(screen.getByText('CALL')).toBeDefined();
      expect(screen.getByText('RM 0.150')).toBeDefined();
      expect(screen.getByText('RM 0.155')).toBeDefined();
      expect(screen.getByText('42.5%')).toBeDefined();
      expect(screen.getByText('WIDE_SPREAD')).toBeDefined();
    });

    it('renders expired banner if warrant has expired', () => {
      const expiredCard: WarrantCardData = {
        code: 'EXPIRED1',
        issuer: 'RHB',
        type: 'put',
        underlying_ticker: 'TENAGA',
        expiry_date: '2026-01-01',
        strike: 12.0,
        display_strike: 'RM 12.00',
        ratio_raw: 5.0,
        display_ratio: '5.00x',
        metrics: {},
        holding_days: 5,
        presets: {},
        flags: [],
        not_evaluated: [],
        evidence_id: 'E9',
        as_of: '2026-10-15T09:00:00Z',
        mode: 'replay',
        expired: true,
      };

      render(<CardTab card={expiredCard} onHoldingDaysChange={vi.fn()} />);
      expect(screen.getByText(/This warrant has expired/i)).toBeDefined();
    });
  });
});
