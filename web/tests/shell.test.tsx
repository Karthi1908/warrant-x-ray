import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DataBadge } from '../src/features/shell/DataBadge';
import { DisclaimerBar } from '../src/features/shell/DisclaimerBar';
import { StatusBanner } from '../src/features/shell/StatusBanner';
import { Header } from '../src/features/shell/Header';
import { Footer } from '../src/features/shell/Footer';

describe('Shell Components', () => {
  describe('DataBadge', () => {
    it('renders live mode badge', () => {
      render(<DataBadge mode="live" asOf="2026-10-16 16:30" />);
      expect(screen.getByText(/Live/i)).toBeDefined();
    });

    it('renders replay mode badge', () => {
      render(<DataBadge mode="replay" asOf="2026-10-16 12:30" />);
      expect(screen.getByText(/Replay/i)).toBeDefined();
    });

    it('renders sample mode badge', () => {
      render(<DataBadge mode="sample" />);
      expect(screen.getByText(/Sample/i)).toBeDefined();
    });
  });

  describe('DisclaimerBar', () => {
    it('renders non-advice disclosure', () => {
      render(<DisclaimerBar />);
      expect(
        screen.getByText(/informational analytics tool and does not provide financial/i)
      ).toBeDefined();
    });
  });

  describe('StatusBanner', () => {
    it('renders alert when degraded or offline', () => {
      render(
        <StatusBanner
          type="warning"
          message="Source feed delayed. Showing replay snapshot."
        />
      );
      expect(screen.getByText(/Source feed delayed/i)).toBeDefined();
    });
  });

  describe('Header', () => {
    it('renders application branding and data mode', () => {
      render(<Header mode="replay" asOf="2026-10-16 16:00" />);
      expect(screen.getByText('Warrant X-Ray')).toBeDefined();
      expect(screen.getByText(/Replay/i)).toBeDefined();
    });

    it('hides chat toggle button when chatEnabled is false', () => {
      render(<Header chatEnabled={false} />);
      expect(screen.queryByRole('button', { name: /Chat/i })).toBeNull();
    });

    it('shows chat toggle button and handles click when chatEnabled is true', () => {
      const onToggle = vi.fn();
      render(<Header chatEnabled={true} chatOpen={false} onToggleChat={onToggle} />);
      const btn = screen.getByRole('button', { name: /Chat/i });
      expect(btn).toBeDefined();
      fireEvent.click(btn);
      expect(onToggle).toHaveBeenCalled();
    });
  });

  describe('Footer', () => {
    it('renders regulatory disclaimer and MIT license notice', () => {
      render(<Footer />);
      expect(screen.getByText(/MIT License/i)).toBeDefined();
      expect(screen.getByText(/Regulatory Disclaimer/i)).toBeDefined();
    });
  });
});
