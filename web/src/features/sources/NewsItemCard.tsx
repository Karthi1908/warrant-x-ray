import React from 'react';
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  ExternalLink,
  Globe,
  Tag,
  Hash,
} from 'lucide-react';
import { cn } from '../../lib/utils';

export interface StatedNumber {
  label: string;
  text: string;
}

export interface NewsItemModel {
  title: string;
  url: string;
  domain: string;
  published_date?: string | null;
  retrieved_at: string;
  event_type: string;
  facts: string[];
  stated_numbers?: StatedNumber[];
  corroboration_count: number;
  unconfirmed: boolean;
  extraction_method?: string;
}

interface NewsItemCardProps {
  item: NewsItemModel;
  onOpenUrl: (url: string, domain: string) => void;
  className?: string;
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  earnings: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  contract: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  dividend: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  director_dealing: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  corporate_action: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
  regulatory: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
  macro: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  other: 'bg-muted text-muted-foreground border-border/50',
};

export const NewsItemCard: React.FC<NewsItemCardProps> = ({ item, onOpenUrl, className }) => {
  const isCorroborated = !item.unconfirmed && item.corroboration_count >= 2;
  const eventStyle = EVENT_TYPE_COLORS[item.event_type] || EVENT_TYPE_COLORS.other;

  return (
    <article
      className={cn(
        'group rounded-xl border border-border/80 bg-card p-4 shadow-xs transition-all hover:border-primary/40 hover:shadow-md flex flex-col justify-between space-y-3',
        className
      )}
    >
      <div>
        {/* Header Badges: Domain, Date, Event Type, Corroboration */}
        <div className="flex flex-wrap items-center gap-1.5 mb-2.5">
          <span className="inline-flex items-center space-x-1 rounded-md bg-muted/80 px-2 py-0.5 text-[11px] font-mono text-muted-foreground border border-border/60">
            <Globe className="h-3 w-3 text-primary/70" />
            <span>{item.domain}</span>
          </span>

          <span
            className={cn(
              'inline-flex items-center space-x-1 rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider border',
              eventStyle
            )}
          >
            <Tag className="h-2.5 w-2.5" />
            <span>{item.event_type.replace('_', ' ')}</span>
          </span>

          {isCorroborated ? (
            <span
              className="inline-flex items-center space-x-1 rounded-md bg-emerald-500/15 text-emerald-400 px-2 py-0.5 text-[11px] font-semibold border border-emerald-500/30"
              title="Corroborated by 2 or more distinct domains"
            >
              <CheckCircle2 className="h-3 w-3" />
              <span>{item.corroboration_count} Sources (Confirmed)</span>
            </span>
          ) : (
            <span
              className="inline-flex items-center space-x-1 rounded-md bg-amber-500/15 text-amber-400 px-2 py-0.5 text-[11px] font-semibold border border-amber-500/30"
              title="Only 1 domain reporting this item"
            >
              <AlertTriangle className="h-3 w-3" />
              <span>1 Source (Unconfirmed)</span>
            </span>
          )}

          {item.published_date && (
            <span className="inline-flex items-center space-x-1 text-[11px] font-mono text-muted-foreground ml-auto">
              <Calendar className="h-3 w-3" />
              <span>{new Date(item.published_date).toLocaleDateString([], { month: 'short', day: 'numeric' })}</span>
            </span>
          )}
        </div>

        {/* Title */}
        <h4 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors leading-snug">
          <button
            type="button"
            onClick={() => onOpenUrl(item.url, item.domain)}
            className="text-left hover:underline inline-flex items-baseline space-x-1"
          >
            <span>{item.title}</span>
            <ExternalLink className="h-3 w-3 inline-block shrink-0 opacity-60 group-hover:opacity-100" />
          </button>
        </h4>

        {/* Unconfirmed Warning Callout */}
        {item.unconfirmed && (
          <div className="mt-2.5 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2 text-amber-400 text-xs flex items-center space-x-2">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            <span className="text-[11px] leading-tight">
              Single-source reporting. Treat facts as provisional until corroborated across independent publishers.
            </span>
          </div>
        )}

        {/* Extracted Facts */}
        {item.facts && item.facts.length > 0 && (
          <ul className="mt-3 space-y-1.5 text-xs text-muted-foreground list-disc list-inside">
            {item.facts.map((fact, idx) => (
              <li key={idx} className="leading-relaxed">
                <span className="text-foreground/90">{fact}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Stated Numbers Chips */}
      {item.stated_numbers && item.stated_numbers.length > 0 && (
        <div className="pt-2 border-t border-border/50 flex flex-wrap gap-1.5 items-center">
          <span className="text-[10px] font-mono uppercase text-muted-foreground mr-1 flex items-center space-x-1">
            <Hash className="h-2.5 w-2.5" />
            <span>Stated Figures:</span>
          </span>
          {item.stated_numbers.map((sn, idx) => (
            <span
              key={idx}
              className="inline-flex items-center space-x-1 rounded bg-muted/60 px-2 py-0.5 text-[11px] font-mono text-foreground border border-border/40"
            >
              <span className="text-muted-foreground">{sn.label}:</span>
              <span className="font-semibold">{sn.text}</span>
            </span>
          ))}
        </div>
      )}
    </article>
  );
};
