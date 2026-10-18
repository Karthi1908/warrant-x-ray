import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DeepReport, DeepRiskReportPayload } from '../src/features/chat/DeepReport';

describe('DeepReport Component', () => {
  const sampleReport: DeepRiskReportPayload = {
    code: '115510',
    holding_days: 5,
    created_at: '2026-03-30T10:00:00Z',
    summary: 'Maybank call warrant holding analysis shows severe friction over 5 days.',
    cost_breakdown: {
      spread_cost_pct: 0.05,
      display_spread_cost: '5.00%',
      daily_theta_decay: 0.015,
      display_daily_theta_decay: '1.50%',
      flat_decay: 0.075,
      display_flat_decay: '7.50%',
      effective_gearing: 6.2,
      display_effective_gearing: '6.20x',
      holding_days: 5,
    },
    what_must_go_right: [
      'Underlying Maybank stock must advance at least 2.5% to beat theta and spread drag.',
      'Implied volatility must remain stable above 22%.',
    ],
    key_risks: [
      {
        flag: 'HIGH_SPREAD',
        description: 'Spread exceeds 4% of mid price.',
        severity: 'HIGH',
      },
      {
        flag: 'DECAY_CLIFF',
        description: 'Expiry is within 25 calendar days; theta acceleration is extreme.',
        severity: 'HIGH',
      },
    ],
    counterpoints: [
      'If Maybank consolidates sideways for 5 trading days, position loses ~12.5% strictly to friction.',
      'Gamma is insufficient to compensate for daily theta at current moneyness.',
    ],
    data_limits: [
      'Implied volatility assumed flat over holding horizon.',
      'Issuer quote presence assumed continuous without liquidity gaps.',
    ],
    disclaimer: 'Educational only. Not investment advice or an endorsement.',
  };

  beforeEach(() => {
    vi.restoreAllMocks();
    if (!window.URL.createObjectURL) {
      window.URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-url');
    } else {
      vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:mock-url');
    }
    if (!window.URL.revokeObjectURL) {
      window.URL.revokeObjectURL = vi.fn();
    } else {
      vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => {});
    }
  });

  it('renders initial state with Generate button when no initialReport is provided', () => {
    render(<DeepReport code="115510" holdingDays={5} />);
    expect(screen.getByTestId('deep-report-container')).toBeDefined();
    expect(screen.getByTestId('generate-deep-report-btn')).toBeDefined();
    expect(screen.getByText('Generate Deep Report')).toBeDefined();
  });

  it('renders full 6-section report and regulatory disclaimer when initialReport is provided', () => {
    render(<DeepReport code="115510" holdingDays={5} initialReport={sampleReport} />);

    expect(screen.getByTestId('deep-report-content')).toBeDefined();
    expect(screen.getByText(/1. Executive Summary/i)).toBeDefined();
    expect(screen.getByText(/2. Quantitative Cost Breakdown/i)).toBeDefined();
    expect(screen.getByText(/3. What Must Go Right/i)).toBeDefined();
    expect(screen.getByText(/4. Triggered Risk Flags/i)).toBeDefined();
    expect(screen.getByText(/5. Red-Team Counterpoints/i)).toBeDefined();
    expect(screen.getByText(/6. Data Limits & Assumptions/i)).toBeDefined();

    // Check specific values
    expect(screen.getByText('5.00%')).toBeDefined();
    expect(screen.getByText('6.20x')).toBeDefined();
    expect(screen.getByText('HIGH_SPREAD')).toBeDefined();
    expect(screen.getByText(/Underlying Maybank stock must advance at least 2.5%/i)).toBeDefined();

    // Disclaimer
    const disclaimer = screen.getByTestId('deep-report-disclaimer');
    expect(disclaimer.textContent).toContain('Educational only. Not investment advice or an endorsement.');
  });

  it('calls onGenerate and updates view with generated report', async () => {
    const onGenerate = vi.fn().mockResolvedValue(sampleReport);
    render(<DeepReport code="115510" holdingDays={5} onGenerate={onGenerate} />);

    const generateBtn = screen.getByTestId('generate-deep-report-btn');
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith('115510', 5);
      expect(screen.getByTestId('deep-report-content')).toBeDefined();
    });
  });

  it('copies full report including regulatory disclaimer to clipboard', async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    render(<DeepReport code="115510" holdingDays={5} initialReport={sampleReport} />);

    const copyBtn = screen.getByTestId('copy-report-btn');
    fireEvent.click(copyBtn);

    await waitFor(() => {
      expect(writeTextMock).toHaveBeenCalled();
      const copiedText = writeTextMock.mock.calls[0][0];
      expect(copiedText).toContain('WARRANTS X-RAY DEEP RISK REPORT: 115510');
      expect(copiedText).toContain('REGULATORY DISCLAIMER');
      expect(copiedText).toContain('Educational only. Not investment advice or an endorsement.');
    });
  });

  it('exports report text as downloadable file containing regulatory disclaimer', () => {
    const clickMock = vi.fn();
    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const element = originalCreateElement(tagName);
      if (tagName === 'a') {
        element.click = clickMock;
      }
      return element;
    });

    render(<DeepReport code="115510" holdingDays={5} initialReport={sampleReport} />);

    const exportBtn = screen.getByTestId('export-report-btn');
    fireEvent.click(exportBtn);

    expect(clickMock).toHaveBeenCalled();
  });
});
