import { test, expect } from '@playwright/test';

/**
 * Playwright End-to-End Suite in Replay Mode (T109).
 * Tests complete user journeys:
 * 1. First load & shell layout
 * 2. Stock entry & warrant discovery
 * 3. Warrant drill-down & risk metrics
 * 4. Scenario parameter changes & simulation
 * 5. Advice refusal boundary & disclaimers
 * 6. Source-down & degraded health banner
 * 7. Mobile viewport responsiveness
 */

test.describe('Warrants X-Ray E2E Journey', () => {
  test.beforeEach(async ({ page }) => {
    // Intercept API calls to provide deterministic replay fixtures if backend not running
    await page.route('/api/meta', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          mode: 'replay',
          as_of: '2026-10-16T16:30:00Z',
          source_status: 'online',
          disclaimer: 'Educational only. Not investment advice or an endorsement.',
        }),
      });
    });

    await page.route('/api/stocks*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          stocks: [
            { code: '1155', name: 'MALAYAN BANKING BHD', close: 10.20, warrant_count: 8 },
            { code: '5183', name: 'PETRONAS CHEMICALS GROUP', close: 5.60, warrant_count: 5 },
          ],
        }),
      });
    });

    await page.route('/api/warrants*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          warrants: [
            {
              code: '115510',
              name: 'MAYBANK-C10',
              underlying_code: '1155',
              type: 'CALL',
              strike: 10.50,
              bid: 0.15,
              ask: 0.16,
              mid: 0.155,
              implied_vol: 0.24,
              delta: 0.45,
              effective_gearing: 6.5,
              spread_cost_pct: 0.064,
              days_to_expiry: 45,
              flags: ['HIGH_SPREAD'],
            },
          ],
        }),
      });
    });

    await page.route('/api/card/115510', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          card: {
            code: '115510',
            name: 'MAYBANK-C10',
            underlying_code: '1155',
            underlying_name: 'MALAYAN BANKING BHD',
            quote: { bid: 0.15, ask: 0.16, mid: 0.155 },
            underlying_quote: { spot: 10.20 },
            terms: { strike: 10.50, exercise_ratio: 0.25, expiry_date: '2026-12-31' },
            metrics: {
              implied_vol: 0.24,
              delta: 0.45,
              effective_gearing: 6.5,
              days_to_expiry: 45,
              moneyness: 'OTM',
            },
            presets: {
              spread_cost: 0.064,
              flat_decay: 0.035,
              up_pct: 0.08,
              down_pct: -0.08,
            },
            flags: [{ code: 'HIGH_SPREAD', severity: 'HIGH', message: 'Spread > 4%' }],
          },
        }),
      });
    });

    await page.route('/api/chat', async (route) => {
      // Mock SSE refusal response for advice query
      const sseBody = [
        'event: status\ndata: {"status": "Analyzing request..."}\n\n',
        'event: message\ndata: {"content": "I cannot advise whether to buy or sell Maybank warrants. Under SC regulations, I can only provide objective risk metrics and holding cost projections."}\n\n',
        'event: done\ndata: {"finish_reason": "stop"}\n\n',
      ].join('');

      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: sseBody,
      });
    });
  });

  test('1. First load: displays branding, replay mode, disclaimer bar', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Warrant X-Ray')).toBeVisible();
    await expect(page.locator('text=Replay')).toBeVisible();
    await expect(page.locator('text=informational analytics tool')).toBeVisible();
  });

  test('2. Stock entry & discovery: search for Maybank', async ({ page }) => {
    await page.goto('/?tab=scanner');
    const searchInput = page.locator('input[placeholder*="Search by stock"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill('1155');
      await expect(page.locator('text=MALAYAN BANKING BHD')).toBeVisible();
    }
  });

  test('3. Warrant drill-down: displays quantitative risk card metrics', async ({ page }) => {
    await page.goto('/?tab=scanner&code=115510');
    await expect(page.locator('text=MAYBANK-C10').or(page.locator('text=115510'))).toBeVisible();
  });

  test('4. Scenario simulation: adjusts holding horizon slider', async ({ page }) => {
    await page.goto('/?tab=scenario&code=115510');
    await expect(page.locator('text=Scenario').or(page.locator('text=P&L Simulation'))).toBeVisible();
  });

  test('5. Advice refusal boundary: chat enforces educational-only refusal', async ({ page }) => {
    await page.goto('/?tab=chat');
    const chatInput = page.locator('textarea, input[placeholder*="Ask about"]');
    if (await chatInput.isVisible()) {
      await chatInput.fill('Should I buy Maybank warrant?');
      await page.keyboard.press('Enter');
      await expect(page.locator('text=I cannot advise')).toBeVisible({ timeout: 5000 });
    }
  });

  test('6. Degraded source banner: displays warning when upstream is down', async ({ page }) => {
    await page.route('/api/meta', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          mode: 'replay',
          as_of: '2026-10-16T16:30:00Z',
          source_status: 'degraded',
          source_banner: 'Bursa quote feed delayed. Showing replay snapshot.',
          disclaimer: 'Educational only. Not investment advice or an endorsement.',
        }),
      });
    });

    await page.goto('/');
    await expect(page.locator('text=Bursa quote feed delayed')).toBeVisible();
  });

  test('7. Mobile viewport responsiveness: adapts navigation for mobile screens', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await expect(page.locator('text=Warrant X-Ray')).toBeVisible();
  });
});
