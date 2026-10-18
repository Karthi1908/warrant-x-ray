import { describe, it, expect, beforeEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import axe from 'axe-core';
import { Header } from '../src/features/shell/Header';
import { Footer } from '../src/features/shell/Footer';
import { DisclaimerBar } from '../src/features/shell/DisclaimerBar';
import { StatusBanner } from '../src/features/shell/StatusBanner';
import { DataBadge } from '../src/features/shell/DataBadge';

describe('Component-level Accessibility (axe-core)', () => {
  beforeEach(() => {
    cleanup();
  });

  it('Header passes axe accessibility rules in light mode', async () => {
    const { container } = render(
      <div className="light">
        <Header mode="live" asOf="2026-10-16 16:30" />
      </div>
    );
    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });

  it('Header passes axe accessibility rules in dark mode', async () => {
    const { container } = render(
      <div className="dark">
        <Header mode="replay" asOf="2026-10-16 12:30" />
      </div>
    );
    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });

  it('DisclaimerBar and StatusBanner pass axe accessibility checks', async () => {
    const { container } = render(
      <div>
        <DisclaimerBar />
        <StatusBanner type="warning" message="Source feed delayed. Showing replay snapshot." />
      </div>
    );
    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });

  it('Footer passes axe accessibility rules', async () => {
    const { container } = render(<Footer />);
    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });

  it('DataBadge supports focus and accessible labeling', async () => {
    const { container } = render(<DataBadge mode="live" asOf="2026-10-16 16:30" />);
    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });
});
