import React from 'react';
import { cn } from '../../lib/utils';
import { ShieldAlert } from 'lucide-react';

export interface DisclaimerBarProps {
  className?: string;
}

export const DisclaimerBar: React.FC<DisclaimerBarProps> = ({ className }) => {
  return (
    <aside
      aria-label="Regulatory Disclaimer"
      className={cn(
        'w-full bg-muted/40 border-b border-border/60 px-4 py-1.5 text-[11px] text-muted-foreground flex items-center justify-center space-x-2 text-center',
        className
      )}
    >
      <ShieldAlert className="h-3.5 w-3.5 text-primary shrink-0" />
      <span>
        <strong>Regulatory Notice:</strong> Warrant X-Ray is an informational analytics tool and does not provide financial, investment, or trading advice. No recommendations, target prices, or predictions are provided.
      </span>
    </aside>
  );
};
