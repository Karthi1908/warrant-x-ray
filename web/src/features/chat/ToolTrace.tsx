import React from 'react';
import { cn } from '../../lib/utils';
import { Loader2, Wrench } from 'lucide-react';

export interface ToolTraceItem {
  name: string;
  text: string;
  step?: number;
}

export interface ToolTraceProps {
  traces: ToolTraceItem[];
  className?: string;
}

export const ToolTrace: React.FC<ToolTraceProps> = ({ traces, className }) => {
  if (!traces || traces.length === 0) return null;

  return (
    <div
      className={cn(
        'rounded-lg border border-border/60 bg-muted/30 p-2.5 my-2 text-xs space-y-1.5',
        className
      )}
    >
      <div className="flex items-center space-x-1.5 text-muted-foreground font-medium">
        <Wrench className="h-3.5 w-3.5" />
        <span>Tool Activity</span>
      </div>
      <div className="space-y-1">
        {traces.map((trace, idx) => (
          <div
            key={`${trace.name}-${idx}`}
            className="flex items-center space-x-2 text-foreground/80 font-mono"
          >
            <Loader2 className="h-3 w-3 animate-spin text-primary shrink-0" />
            <span>{trace.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
