import React from 'react';
import { cn } from '../../lib/utils';

export interface CitationChipProps {
  evidenceId: string;
  summary?: string;
  onClick?: (evidenceId: string) => void;
  className?: string;
}

export const CitationChip: React.FC<CitationChipProps> = ({
  evidenceId,
  summary,
  onClick,
  className,
}) => {
  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    if (onClick) {
      onClick(evidenceId);
    }
  };

  const idText = evidenceId.startsWith('[') ? evidenceId : `[${evidenceId}]`;

  return (
    <button
      type="button"
      onClick={handleClick}
      title={summary || `Evidence citation ${evidenceId}`}
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 mx-0.5 text-xs font-mono font-medium rounded',
        'bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-colors',
        'focus:outline-none focus:ring-1 focus:ring-primary',
        className
      )}
    >
      {idText}
    </button>
  );
};
