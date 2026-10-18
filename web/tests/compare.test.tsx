import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import {
  CompareGrid,
  CompareTab,
  type ComparedWarrantItem,
  type WarrantComparisonResult,
} from '../src/features/compare';

describe('Warrant Comparison Components (T097 - Principle III & AC-05)', () => {
  const mockComparedItems: ComparedWarrantItem[] = [
    {
      code: '1155C1',
      issuer: 'KENANGA',
      type: 'call',
      underlying_ticker: 'MAYBANK',
      underlying_price: 10.5,
      display_underlying_price: 'RM 10.50',
      strike: 10.5,
      display_strike: 'RM 10.50',
      ratio: 5.0,
      display_ratio: '5 : 1',
      expiry_date: '2027-02-13',
      days_to_expiry: 118,
      display_days_to_expiry: '118d',
      bid: 0.15,
      display_bid: 'RM 0.15',
      ask: 0.16,
      display_ask: 'RM 0.16',
      mid: 0.155,
      display_mid: 'RM 0.155',
      spread_pct: 0.065,
      display_spread_pct: '6.5%',
      effective_gearing: 6.2,
      display_effective_gearing: '6.2x',
      headline_iv: 0.28,
      display_headline_iv: '28.0%',
      spread_cost: 0.065,
      display_spread_cost: '6.5%',
      flat_decay: 0.035,
      display_flat_decay: '-3.5%',
      iv_crush: 0.045,
      display_iv_crush: '-4.5%',
      breakeven_move: 0.012,
      display_breakeven_move: '+1.2%',
      flags: [],
    },
    {
      code: '1155C2',
      issuer: 'MACQUARIE',
      type: 'call',
      underlying_ticker: 'MAYBANK',
      underlying_price: 10.5,
      display_underlying_price: 'RM 10.50',
      strike: 11.0,
      display_strike: 'RM 11.00',
      ratio: 6.0,
      display_ratio: '6 : 1',
      expiry_date: '2027-03-25',
      days_to_expiry: 158,
      display_days_to_expiry: '158d',
      bid: 0.09,
      display_bid: 'RM 0.09',
      ask: 0.11,
      display_ask: 'RM 0.11',
      mid: 0.10,
      display_mid: 'RM 0.100',
      spread_pct: 0.2,
      display_spread_pct: '20.0%',
      effective_gearing: 8.1,
      display_effective_gearing: '8.1x',
      headline_iv: 0.32,
      display_headline_iv: '32.0%',
      spread_cost: 0.2,
      display_spread_cost: '20.0%',
      flat_decay: 0.055,
      display_flat_decay: '-5.5%',
      iv_crush: 0.06,
      display_iv_crush: '-6.0%',
      breakeven_move: 0.032,
      display_breakeven_move: '+3.2%',
      flags: [
        {
          code: 'WIDE_SPREAD',
          severity: 'warn',
          threshold: '> 10.0%',
          value: '20.0%',
          text: 'Wide bid-ask spread of 20.0% creates high round-trip cost.',
        },
      ],
    },
  ];

  it('renders CompareGrid with uniform side-by-side attributes and NO ranking / best labels (AC-05)', () => {
    render(
      <CompareGrid warrants={mockComparedItems} holdingDays={5} />
    );

    // Verify both warrant codes are headers
    expect(screen.getByText('1155C1')).toBeDefined();
    expect(screen.getByText('1155C2')).toBeDefined();

    // Verify attribute rows
    expect(screen.getByText('KENANGA')).toBeDefined();
    expect(screen.getByText('MACQUARIE')).toBeDefined();
    expect(screen.getByText('RM 10.50')).toBeDefined();
    expect(screen.getByText('RM 11.00')).toBeDefined();
    expect(screen.getByText('6.2x')).toBeDefined();
    expect(screen.getByText('8.1x')).toBeDefined();
    expect(screen.getByText('WIDE_SPREAD')).toBeDefined();

    // Verify Constitution Principle III notice
    expect(screen.getByText(/Constitution Principle III:/i)).toBeDefined();

    // Principle III Strict Verification: NO ranking, NO winner, NO recommendation, NO scores
    expect(screen.queryByText(/winner/i)).toBeNull();
    expect(screen.queryByText(/rank #/i)).toBeNull();
    expect(screen.queryByText(/recommendation/i)).toBeNull();
    expect(screen.queryByText(/score:/i)).toBeNull();
    expect(screen.queryByText(/^best$/i)).toBeNull();
    expect(screen.queryByText(/best warrant/i)).toBeNull();
  });

  it('renders CompareTab with API fetch and holding days stepper interaction', async () => {
    const mockResponse: WarrantComparisonResult = {
      underlying_ticker: 'MAYBANK',
      holding_days: 5,
      comparison: mockComparedItems,
      as_of: '2026-10-16T12:00:00Z',
      mode: 'live',
      evidence_id: 'E1',
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    render(<CompareTab initialCodes={['1155C1', '1155C2']} />);

    await waitFor(() => {
      expect(screen.getByText('1155C1')).toBeDefined();
      expect(screen.getByText('1155C2')).toBeDefined();
    });

    // Change horizon to 10d
    fireEvent.click(screen.getByText('10d'));

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/compare',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          codes: ['1155C1', '1155C2'],
          holding_days: 10,
        }),
      })
    );
  });

  it('renders error banner when backend rejects mixed underlyings (HTTP 400)', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: () =>
        Promise.resolve({
          detail: 'Comparison requires warrants on the same underlying stock. Found mixed underlyings: CIMB, MAYBANK',
        }),
    });

    render(<CompareTab initialCodes={['1155C1', 'CIMB-C1']} />);

    await waitFor(() => {
      expect(
        screen.getByText(/Comparison requires warrants on the same underlying stock/i)
      ).toBeDefined();
    });
  });
});
