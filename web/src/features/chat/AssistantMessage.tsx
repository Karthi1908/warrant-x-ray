import React from 'react';
import { cn } from '../../lib/utils';
import { CitationChip } from './CitationChip';
import { ShieldCheck, AlertCircle } from 'lucide-react';

export interface AssistantMessageProps {
  content: string;
  isPartial?: boolean;
  isVerified?: boolean;
  onCitationClick?: (evidenceId: string) => void;
  className?: string;
}

export const AssistantMessage: React.FC<AssistantMessageProps> = ({
  content,
  isPartial = false,
  isVerified = true,
  onCitationClick,
  className,
}) => {
  // Parse text into regular segments and citation chips [E#]
  const renderFormattedContent = (text: string) => {
    const parts = text.split(/(\[E\d+\])/g);

    return parts.map((part, index) => {
      const match = part.match(/^\[(E\d+)\]$/);
      if (match) {
        const evidenceId = match[1];
        return (
          <CitationChip
            key={`${evidenceId}-${index}`}
            evidenceId={evidenceId}
            onClick={onCitationClick}
          />
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className={cn('space-y-2 rounded-xl bg-card border border-border/80 p-3.5 shadow-sm', className)}>
      <div className="flex items-center justify-between text-xs border-b border-border/40 pb-1.5 mb-2">
        <div className="flex items-center space-x-1.5 font-medium text-foreground">
          <span className="h-2 w-2 rounded-full bg-primary" />
          <span>Risk Copilot</span>
        </div>
        <div className="flex items-center space-x-2">
          {isVerified && (
            <span className="inline-flex items-center space-x-1 text-[11px] text-emerald-500 font-medium">
              <ShieldCheck className="h-3 w-3" />
              <span>Grounded</span>
            </span>
          )}
          {isPartial && (
            <span className="inline-flex items-center space-x-1 text-[11px] text-amber-500 font-medium">
              <AlertCircle className="h-3 w-3" />
              <span>Partial</span>
            </span>
          )}
        </div>
      </div>

      <div className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap">
        {renderFormattedContent(content)}
      </div>

      <div className="pt-2 border-t border-border/40 flex items-center justify-between text-[11px] text-muted-foreground italic">
        <span>Describe, never advise. Figures computed deterministically.</span>
      </div>
    </div>
  );
};
