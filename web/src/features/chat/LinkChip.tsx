import React from 'react';
import type { ViewLinkData } from '../../api/sse';
import {
  Sliders,
  TrendingUp,
  Layers,
  Search,
  Database,
  HeartPulse,
  Newspaper,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';

interface LinkChipProps {
  link: ViewLinkData;
  onClick?: (href: string, link: ViewLinkData) => void;
}

export function LinkChip({ link, onClick }: LinkChipProps): React.JSX.Element {
  const isExternal = link.kind === 'news' || link.href.startsWith('http');

  const getIcon = () => {
    switch (link.kind) {
      case 'card':
        return <Sliders className="w-3.5 h-3.5 text-cyan-400" />;
      case 'scenario':
        return <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />;
      case 'compare':
        return <Layers className="w-3.5 h-3.5 text-violet-400" />;
      case 'stock':
        return <Search className="w-3.5 h-3.5 text-amber-400" />;
      case 'sources':
        return <Database className="w-3.5 h-3.5 text-slate-400" />;
      case 'health':
        return <HeartPulse className="w-3.5 h-3.5 text-rose-400" />;
      case 'news':
        return <Newspaper className="w-3.5 h-3.5 text-blue-400" />;
      default:
        return <ChevronRight className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  if (isExternal) {
    return (
      <a
        href={link.href}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800/90 border border-slate-700/80 text-slate-200 hover:text-white hover:bg-slate-700/80 hover:border-slate-600 transition-all shadow-sm group"
      >
        {getIcon()}
        <span>{link.label}</span>
        <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-cyan-400 transition-colors ml-0.5" />
      </a>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onClick?.(link.href, link)}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800/90 border border-slate-700/80 text-slate-200 hover:text-white hover:bg-slate-700/80 hover:border-cyan-500/50 hover:shadow-[0_0_12px_rgba(6,182,212,0.15)] transition-all cursor-pointer group"
    >
      {getIcon()}
      <span>{link.label}</span>
      <ChevronRight className="w-3 h-3 text-slate-400 group-hover:translate-x-0.5 transition-transform ml-0.5" />
    </button>
  );
}
