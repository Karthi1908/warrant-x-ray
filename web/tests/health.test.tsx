import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HealthTab } from '../src/features/health/HealthTab';

describe('Health Feature Component (T083)', () => {
  it('renders operational health titles and metrics categories', () => {
    render(<HealthTab />);

    expect(screen.getByText(/System Health & Operational Status/i)).toBeDefined();
    expect(screen.getAllByText(/Public Usage Metrics/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Total Visits/i)).toBeDefined();
    expect(screen.getByText(/Daily Uniques/i)).toBeDefined();
    expect(screen.getByText(/Interactive Queries/i)).toBeDefined();
    expect(screen.getByText(/LLM Model Routing & Tier Health/i)).toBeDefined();
    expect(screen.getByText(/Bursa Market Status/i)).toBeDefined();
  });
});
