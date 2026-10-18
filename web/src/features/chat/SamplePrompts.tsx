import React from 'react';
import { cn } from '../../lib/utils';
import { Sparkles } from 'lucide-react';

export interface SamplePrompt {
  id: string;
  category: string;
  label: string;
  prompt: string;
}

export const DEFAULT_SAMPLES: SamplePrompt[] = [
  {
    id: 'holding-cost-115510',
    category: 'Cost',
    label: 'Holding cost for 115510',
    prompt: 'What does holding MAYBANK-C28 (115510) for 5 days actually cost?',
  },
  {
    id: 'scenario-5pct',
    category: 'Scenario',
    label: 'Maybank +5% move in 3 days',
    prompt: 'If Maybank shares rise by 5% over 3 days, what is the expected warrant P&L?',
  },
  {
    id: 'compare-c28-c29',
    category: 'Compare',
    label: 'Compare MAYBANK-C28 vs C29',
    prompt: 'Compare MAYBANK-C28 and MAYBANK-C29 without ranking them.',
  },
  {
    id: 'explain-move',
    category: 'Attribution',
    label: 'Why did price drop when stock rose?',
    prompt: 'Why did my warrant drop in price when the underlying share rose yesterday?',
  },
];

export interface SamplePromptsProps {
  onSelect: (prompt: string) => void;
  className?: string;
}

export const SamplePrompts: React.FC<SamplePromptsProps> = ({ onSelect, className }) => {
  const getCategoryBadgeClass = (category: string) => {
    switch (category.toLowerCase()) {
      case 'cost':
        return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20';
      case 'scenario':
        return 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20';
      case 'compare':
        return 'bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20';
      case 'attribution':
      default:
        return 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20';
    }
  };

  return (
    <div className={cn('space-y-2 p-1', className)}>
      <div className="flex items-center space-x-1.5 text-xs text-muted-foreground font-semibold">
        <Sparkles className="h-3.5 w-3.5 text-indigo-500" />
        <span>Try instant risk queries:</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {DEFAULT_SAMPLES.map((sample) => (
          <button
            key={sample.id}
            type="button"
            onClick={() => onSelect(sample.prompt)}
            className={cn(
              'flex items-center justify-between text-left p-2 rounded-xl border border-border/80 bg-card',
              'hover:border-indigo-400 hover:bg-indigo-50/50 dark:hover:bg-indigo-950/40 hover:shadow-xs transition-all duration-150 group'
            )}
          >
            <span className="text-xs font-medium text-foreground group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors pr-2">
              {sample.label}
            </span>
            <span
              className={cn(
                'text-[10px] font-mono font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded border shrink-0',
                getCategoryBadgeClass(sample.category)
              )}
            >
              {sample.category}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};
