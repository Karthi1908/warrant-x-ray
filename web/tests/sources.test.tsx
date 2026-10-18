import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SourcesTab, NewsItemCard, EvidenceRecord, ExternalLinkModal } from '../src/features/sources';

describe('Sources and News Components (T092)', () => {
  const mockItem = {
    title: 'Maybank records quarterly profit growth [ILLUSTRATIVE]',
    url: 'https://theedgemalaysia.com/article/maybank-q3',
    domain: 'theedgemalaysia.com',
    published_date: '2026-10-15T08:30:00Z',
    retrieved_at: '2026-10-16T00:00:00Z',
    event_type: 'earnings',
    facts: ['Net profit grew 12% year-on-year', 'Retail deposits remained resilient'],
    stated_numbers: [{ label: 'Net Profit', text: 'RM 2.5B' }],
    corroboration_count: 2,
    unconfirmed: false,
  };

  const mockUnconfirmedItem = {
    ...mockItem,
    corroboration_count: 1,
    unconfirmed: true,
  };

  const mockEvidence = {
    id: 'E1',
    kind: 'news',
    source: 'tavily',
    as_of: '2026-10-16T12:00:00Z',
    summary: '7-day news context for MAYBANK (2 items)',
    payload: { ticker: 'MAYBANK' },
    allowlist: ['MAYBANK', 'RM 2.5B', '12%'],
  };

  it('renders NewsItemCard with domain, confirmed corroboration badge, facts, and stated numbers', () => {
    const handleOpen = vi.fn();
    render(<NewsItemCard item={mockItem} onOpenUrl={handleOpen} />);

    expect(screen.getByText('theedgemalaysia.com')).toBeDefined();
    expect(screen.getByText(/2 Sources \(Confirmed\)/i)).toBeDefined();
    expect(screen.getByText(/earnings/i)).toBeDefined();
    expect(screen.getByText(/Net profit grew 12%/i)).toBeDefined();
    expect(screen.getByText('Net Profit:')).toBeDefined();
    expect(screen.getByText('RM 2.5B')).toBeDefined();

    // Clicking title triggers URL callback
    fireEvent.click(screen.getByText(/Maybank records quarterly profit growth/i));
    expect(handleOpen).toHaveBeenCalledWith('https://theedgemalaysia.com/article/maybank-q3', 'theedgemalaysia.com');
  });

  it('renders unconfirmed callout for single-domain news items', () => {
    render(<NewsItemCard item={mockUnconfirmedItem} onOpenUrl={vi.fn()} />);

    expect(screen.getByText(/1 Source \(Unconfirmed\)/i)).toBeDefined();
    expect(screen.getByText(/Single-source reporting/i)).toBeDefined();
  });

  it('renders EvidenceRecord expander and allowlist tokens', () => {
    render(<EvidenceRecord evidence={mockEvidence} />);

    expect(screen.getByText('E1')).toBeDefined();
    expect(screen.getByText(/Grounding Evidence Envelope/i)).toBeDefined();
    expect(screen.getByText(/7-day news context for MAYBANK/i)).toBeDefined();

    // Click to expand
    fireEvent.click(screen.getByText(/Grounding Evidence Envelope/i));
    expect(screen.getByText(/Allowed Verifier Tokens \(3\)/i)).toBeDefined();
    expect(screen.getByText('RM 2.5B')).toBeDefined();
  });

  it('renders ExternalLinkModal with safety warning and triggers cancel / confirm', () => {
    const handleClose = vi.fn();
    const { rerender } = render(
      <ExternalLinkModal
        isOpen={false}
        url="https://theedgemalaysia.com/article/test"
        domain="theedgemalaysia.com"
        onClose={handleClose}
      />
    );

    expect(screen.queryByText(/External Link Safety Warning/i)).toBeNull();

    rerender(
      <ExternalLinkModal
        isOpen={true}
        url="https://theedgemalaysia.com/article/test"
        domain="theedgemalaysia.com"
        onClose={handleClose}
      />
    );

    expect(screen.getByText(/External Link Safety Warning/i)).toBeDefined();
    expect(screen.getAllByText(/theedgemalaysia.com/i).length).toBeGreaterThan(0);

    // Click cancel
    fireEvent.click(screen.getByText('Cancel'));
    expect(handleClose).toHaveBeenCalled();
  });

  it('renders SourcesTab with preset ticker quick filters and 7-day window notice', () => {
    render(<SourcesTab />);

    expect(screen.getByText(/Cited News & Source Grounding/i)).toBeDefined();
    expect(screen.getByText(/Strict 7-Day Window/i)).toBeDefined();
    expect(screen.getByText('MAYBANK')).toBeDefined();
    expect(screen.getByText('TENAGA')).toBeDefined();
    expect(screen.getByText('PBBANK')).toBeDefined();
    expect(screen.getByText('INARI')).toBeDefined();
  });
});
