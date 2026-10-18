import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ScenarioSliders } from '../src/features/scenario/ScenarioSliders';
import { PnlChart } from '../src/features/scenario/PnlChart';
import { AssumptionsNote } from '../src/features/scenario/AssumptionsNote';

// Polyfill ResizeObserver for Recharts ResponsiveContainer in jsdom
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};


describe('Scenario Feature Components', () => {
  describe('ScenarioSliders', () => {
    it('renders move, days, and iv shift controls with reset button', () => {
      const onChange = vi.fn();
      const onReset = vi.fn();

      render(
        <ScenarioSliders
          move={0.05}
          days={3}
          ivShift={-5.0}
          maxDays={60}
          onChange={onChange}
          onReset={onReset}
        />
      );

      expect(screen.getByText(/Underlying Stock Move/i)).toBeDefined();
      expect(screen.getByText(/Holding Period/i)).toBeDefined();
      expect(screen.getByText(/Implied Volatility Shift/i)).toBeDefined();

      const resetBtn = screen.getByRole('button', { name: /reset/i });
      fireEvent.click(resetBtn);
      expect(onReset).toHaveBeenCalled();
    });

    it('renders presets and triggers preset change', () => {
      const onPresetSelect = vi.fn();

      render(
        <ScenarioSliders
          move={0.0}
          days={0}
          ivShift={0.0}
          maxDays={60}
          onChange={vi.fn()}
          onPresetSelect={onPresetSelect}
        />
      );

      const presetBtn = screen.getByText(/Bullish: \+5% in 3d/i);
      expect(presetBtn).toBeDefined();

      fireEvent.click(presetBtn);
      expect(onPresetSelect).toHaveBeenCalledWith({
        move: 0.05,
        days: 3,
        ivShift: -5.0,
      });
    });
  });

  describe('PnlChart', () => {
    it('renders breakeven annotation and horizon legend', () => {
      const curves = [
        {
          horizon_days: 0,
          display_horizon: 'Day 0 (Immediate)',
          points: [
            { move: -0.05, display_move: '-5%', pnl_pct: -0.15, display_pnl_pct: '-15.0%' },
            { move: 0.0, display_move: '0%', pnl_pct: -0.062, display_pnl_pct: '-6.2%' },
            { move: 0.05, display_move: '+5%', pnl_pct: 0.22, display_pnl_pct: '+22.0%' },
          ],
        },
        {
          horizon_days: 5,
          display_horizon: 'Day 5',
          points: [
            { move: -0.05, display_move: '-5%', pnl_pct: -0.22, display_pnl_pct: '-22.0%' },
            { move: 0.0, display_move: '0%', pnl_pct: -0.12, display_pnl_pct: '-12.0%' },
            { move: 0.05, display_move: '+5%', pnl_pct: 0.14, display_pnl_pct: '+14.0%' },
          ],
        },
      ];

      render(
        <PnlChart
          curves={curves}
          breakevenMove={0.024}
          displayBreakeven="+2.4%"
          currentMove={0.05}
          currentPnl={0.14}
        />
      );

      expect(screen.getByText(/Breakeven: \+2.4%/i)).toBeDefined();
      expect(screen.getByText(/Day 0 \(Immediate\)/i)).toBeDefined();
    });
  });

  describe('AssumptionsNote', () => {
    it('renders deterministic assumptions list', () => {
      const assumptions = [
        'Exit priced at model bid based on constant 3.0% risk-free rate',
        'Implied volatility shifts uniformly across remaining term',
        'No cash dividend adjustments assumed during simulation window',
      ];

      render(<AssumptionsNote assumptions={assumptions} />);

      expect(screen.getByText(/Model Assumptions/i)).toBeDefined();
      expect(screen.getByText(/Exit priced at model bid/i)).toBeDefined();
      expect(screen.getByText(/No cash dividend adjustments/i)).toBeDefined();
    });
  });
});
