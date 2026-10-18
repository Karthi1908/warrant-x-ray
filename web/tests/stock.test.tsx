import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import {
  StockOverviewBar,
  NearestWarrantsList,
  WarrantTable,
  StockTab,
  type StockSummary,
  type WarrantListItem,
} from '../src/features/stock';

describe('Stock Screener and Overview Components (T096)', () => {
  const mockSummary: StockSummary = {
    ticker: 'MAYBANK',
    as_of: '2026-10-16T12:00:00Z',
    underlying_price: 10.5,
    display_underlying_price: 'RM 10.50',
    call_count: 14,
    put_count: 3,
    issuer_count: 4,
    issuers: ['KENANGA', 'MACQUARIE', 'CGS', 'RHB'],
    min_expiry: '2026-11-20',
    max_expiry: '2027-05-15',
    median_spread_pct: 0.042,
    display_median_spread_pct: '4.2%',
    median_flat_decay: 0.055,
    display_median_flat_decay: '5.5%',
    flag_counts: {
      SHORT_EXPIRY: 2,
      WIDE_SPREAD: 3,
    },
    nearest_warrants: [
      {
        code: '1155C1',
        type: 'call',
        strike: 10.5,
        display_strike: 'RM 10.50',
        distance_from_strike: 0.0,
        display_distance_from_strike: 'RM 0.00',
        bid: 0.15,
        display_bid: 'RM 0.15',
        ask: 0.16,
        display_ask: 'RM 0.16',
        days_to_expiry: 45,
        display_days_to_expiry: '45d',
        effective_gearing: 6.2,
        display_effective_gearing: '6.2x',
      },
      {
        code: '1155C2',
        type: 'call',
        strike: 10.8,
        display_strike: 'RM 10.80',
        distance_from_strike: 0.3,
        display_distance_from_strike: 'RM 0.30',
        bid: 0.11,
        display_bid: 'RM 0.11',
        ask: 0.12,
        display_ask: 'RM 0.12',
        days_to_expiry: 60,
        display_days_to_expiry: '60d',
        effective_gearing: 7.5,
        display_effective_gearing: '7.5x',
      },
    ],
    volatility_10d: 0.18,
    display_volatility_10d: '18.0%',
    volatility_30d: 0.195,
    display_volatility_30d: '19.5%',
    evidence_id: 'E1',
  };

  const mockWarrants: WarrantListItem[] = [
    {
      code: '1155C1',
      issuer: 'KENANGA',
      type: 'call',
      underlying_ticker: 'MAYBANK',
      expiry_date: '2027-02-13',
      strike: 10.5,
      display_strike: 'RM 10.50',
      ratio_raw: 5.0,
      display_ratio: '5 : 1',
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
      days_to_expiry: 118,
      display_days_to_expiry: '118d',
      flags_count: 0,
    },
    {
      code: '1155C2',
      issuer: 'MACQUARIE',
      type: 'call',
      underlying_ticker: 'MAYBANK',
      expiry_date: '2027-03-25',
      strike: 11.0,
      display_strike: 'RM 11.00',
      ratio_raw: 6.0,
      display_ratio: '6 : 1',
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
      days_to_expiry: 158,
      display_days_to_expiry: '158d',
      flags_count: 1,
    },
  ];

  it('renders StockOverviewBar with price, counts, medians, and active issuers', () => {
    render(<StockOverviewBar summary={mockSummary} />);

    expect(screen.getByText('MAYBANK')).toBeDefined();
    expect(screen.getByText('RM 10.50')).toBeDefined();
    expect(screen.getByText(/14 Calls/i)).toBeDefined();
    expect(screen.getByText(/3 Puts/i)).toBeDefined();
    expect(screen.getByText('4.2%')).toBeDefined();
    expect(screen.getByText('5.5%')).toBeDefined();
    expect(screen.getByText('19.5%')).toBeDefined();
    expect(screen.getByText(/KENANGA, MACQUARIE/i)).toBeDefined();
    expect(screen.getByText('SHORT_EXPIRY')).toBeDefined();
    expect(screen.getByText('WIDE_SPREAD')).toBeDefined();
  });

  it('renders NearestWarrantsList with ATM candidates and selection toggle', () => {
    const handleToggle = vi.fn();
    const handleInspect = vi.fn();

    render(
      <NearestWarrantsList
        nearest={mockSummary.nearest_warrants}
        selectedCodes={['1155C1']}
        onToggleSelect={handleToggle}
        onInspect={handleInspect}
      />
    );

    expect(screen.getByText('1155C1')).toBeDefined();
    expect(screen.getByText('1155C2')).toBeDefined();
    expect(screen.getByText('Selected')).toBeDefined();

    fireEvent.click(screen.getByRole('button', { name: /^compare$/i }));
    expect(handleToggle).toHaveBeenCalledWith('1155C2');
  });

  it('renders WarrantTable with columns, spread styling, and sort triggers', () => {
    const handleSort = vi.fn();
    const handleToggle = vi.fn();

    render(
      <WarrantTable
        warrants={mockWarrants}
        selectedCodes={[]}
        onToggleSelect={handleToggle}
        sortField="strike"
        sortOrder="asc"
        onSortChange={handleSort}
        ivBasis="mid"
      />
    );

    expect(screen.getByText('1155C1')).toBeDefined();
    expect(screen.getByText('1155C2')).toBeDefined();
    expect(screen.getByText('6.5%')).toBeDefined();
    expect(screen.getByText('20.0%')).toBeDefined();
    expect(screen.getByText('6.2x')).toBeDefined();
    expect(screen.getByText('28.0%')).toBeDefined();

    // Trigger sort on spread
    fireEvent.click(screen.getByText('Spread'));
    expect(handleSort).toHaveBeenCalledWith('spread_pct');
  });

  it('renders explicit empty state when warrants array is empty (AC-05, CHK016)', () => {
    render(
      <WarrantTable
        warrants={[]}
        selectedCodes={[]}
        onToggleSelect={vi.fn()}
        sortField="strike"
        sortOrder="asc"
        onSortChange={vi.fn()}
        ivBasis="mid"
      />
    );

    expect(
      screen.getByText('No Warrants Found for this Selection')
    ).toBeDefined();
    expect(
      screen.getByText(/There are currently no listed structured warrants matching your filter criteria/i)
    ).toBeDefined();
  });

  it('renders StockTab and integrates fetch calls for summary and warrants list', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/stock/MAYBANK')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes('/api/warrants')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              results: mockWarrants,
              count: 2,
              total: 2,
              iv_basis: 'mid',
            }),
        });
      }
      return Promise.reject(new Error('Unknown url'));
    });

    render(<StockTab initialTicker="MAYBANK" />);

    await waitFor(() => {
      expect(screen.getAllByText('MAYBANK').length).toBeGreaterThan(0);
      expect(screen.getAllByText('1155C1').length).toBeGreaterThan(0);
    });
  });
});
