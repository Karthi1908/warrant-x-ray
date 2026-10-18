import React from 'react';
import { cn } from '../../lib/utils';
import { Info, Check } from 'lucide-react';

export interface AssumptionsNoteProps {
  assumptions: string[];
  className?: string;
}

export const AssumptionsNote: React.FC<AssumptionsNoteProps> = ({
  assumptions,
  className,
}) => {
  if (!assumptions || assumptions.length === 0) return null;

  return (
    <div
      className={cn(
        'rounded-xl border border-border/80 bg-muted/20 p-3.5 space-y-2 text-xs text-muted-foreground',
        className
      )}
    >
      <div className="flex items-center space-x-1.5 font-medium text-foreground">
        <Info className="h-3.5 w-3.5 text-primary" />
        <span>Model Assumptions</span>
      </div>

      <ul className="space-y-1 pl-1">
        {assumptions.map((item, idx) => (
          <li key={idx} className="flex items-start space-x-2">
            <Check className="h-3.5 w-3.5 text-primary/70 shrink-0 mt-0.5" />
            <span className="leading-relaxed">{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};
