import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from '../src/App';
import { SAMPLE_CARD } from '../src/features/card/sample';

describe('Deep Link Synchronization (T028)', () => {
  beforeEach(() => {
    // Mock global fetch for /api/meta, underlyings, stock summary, and warrant lookups
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) => {
        if (url.includes('/api/meta')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                mode: 'sample',
                as_of: '2026-10-27T10:00:00Z',
                market_open: true,
                stale: false,
                chat_enabled: true,
              }),
          });
        }
        if (url.includes('/api/warrants?')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                total: 0,
                results: [],
              }),
          });
        }
        if (url.includes('/api/warrants/')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                ...SAMPLE_CARD,
                code: '532641',
                underlying_ticker: 'MAYBANK',
              }),
          });
        }
        if (url.includes('/api/underlyings')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                underlyings: [
                  { ticker: 'MAYBANK', name: 'Malayan Banking Berhad', warrant_count: 5 },
                ],
              }),
          });
        }
        if (url.includes('/api/stock/')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                ticker: 'MAYBANK',
                as_of: '2026-10-27T10:00:00Z',
                underlying_price: 10.2,
                display_underlying_price: 'RM 10.20',
                call_count: 5,
                put_count: 0,
                issuer_count: 1,
                issuers: ['CGS'],
                nearest_warrants: [],
                flag_counts: {},
                evidence_id: 'E1',
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        });
      })
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState(null, '', '/');
  });

  it('opens the card tab when URL contains tab=card', async () => {
    window.history.replaceState(null, '', '/?tab=card&code=532641&days=5');
    render(<App />);

    await waitFor(() => {
      // The active card code 532641 should be rendered
      expect(screen.getAllByText('532641').length).toBeGreaterThan(0);
    });
  });

  it('falls back to default stock tab when tab param is invalid', async () => {
    window.history.replaceState(null, '', '/?tab=invalid_tab');
    render(<App />);

    await waitFor(() => {
      // Default tab has Stock Screener
      expect(screen.getByText('Stock Screener')).toBeDefined();
    });
  });

  it('opens the scenario tab when URL contains tab=scenario&code=532641', async () => {
    window.history.replaceState(null, '', '/?tab=scenario&code=532641');
    render(<App />);

    await waitFor(() => {
      expect(screen.getAllByText('532641').length).toBeGreaterThan(0);
    });
  });

  it('renders chat toggle when chat_enabled is true in meta response', async () => {
    render(<App />);

    await waitFor(() => {
      const chatBtn = screen.getByRole('button', { name: /Chat/i });
      expect(chatBtn).toBeDefined();
    });
  });
});

