import React from 'react';
import { cn } from '../../lib/utils';
import { ShieldCheck } from 'lucide-react';

export interface FooterProps {
  className?: string;
}

export const Footer: React.FC<FooterProps> = ({ className }) => {
  return (
    <footer
      className={cn(
        'border-t border-border bg-card/40 px-6 py-4 text-xs text-muted-foreground flex flex-col md:flex-row items-center justify-between gap-3',
        className
      )}
    >
      <div className="flex items-center space-x-2">
        <ShieldCheck className="h-4 w-4 text-primary" />
        <span>
          Warrant X-Ray &copy; 2026. Released under the{' '}
          <span className="font-medium text-foreground underline decoration-dotted">
            MIT License
          </span>
          .
        </span>
      </div>

      <div className="text-[11px] text-center md:text-right max-w-xl">
        <p>
          <strong>Regulatory Disclaimer:</strong> An informational analytics tool and does not provide financial, investment, or trading advice.
          Metrics are computed deterministically.
        </p>
      </div>
    </footer>
  );
};
