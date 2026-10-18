import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Database, ShieldCheck, Tag, Terminal } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface EvidencePayload {
  id: string;
  kind: string;
  source: string;
  as_of: string;
  summary: string;
  payload: Record<string, unknown>;
  allowlist?: string[];
}

interface EvidenceRecordProps {
  evidence: EvidencePayload | null;
  className?: string;
}

export const EvidenceRecord: React.FC<EvidenceRecordProps> = ({ evidence, className }) => {
  const [expanded, setExpanded] = useState(false);
  const [showJson, setShowJson] = useState(false);

  if (!evidence) {
    return null;
  }

  const allowlist = evidence.allowlist || [];

  return (
    <div
      className={cn(
        'rounded-xl border border-border/80 bg-card/60 backdrop-blur-xs p-3 shadow-xs transition-all',
        className
      )}
    >
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded(!expanded)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setExpanded(!expanded);
          }
        }}
        className="flex items-center justify-between cursor-pointer select-none"
      >
        <div className="flex items-center space-x-2.5">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10 text-primary border border-primary/20 text-xs font-mono font-bold">
            {evidence.id || 'E1'}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold tracking-tight text-foreground">
                Grounding Evidence Envelope
              </span>
              <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] font-mono text-muted-foreground uppercase">
                {evidence.source}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground line-clamp-1">{evidence.summary}</p>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-muted-foreground">
          <span className="text-[10px] font-mono hidden sm:inline">
            {new Date(evidence.as_of).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-border/60 space-y-3 text-xs">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <div className="rounded-lg bg-muted/40 p-2 border border-border/40">
              <div className="flex items-center space-x-1.5 text-muted-foreground text-[10px] uppercase font-mono">
                <Database className="h-3 w-3" />
                <span>Verification Source</span>
              </div>
              <p className="font-semibold text-foreground mt-0.5 capitalize">{evidence.source}</p>
            </div>

            <div className="rounded-lg bg-muted/40 p-2 border border-border/40">
              <div className="flex items-center space-x-1.5 text-muted-foreground text-[10px] uppercase font-mono">
                <ShieldCheck className="h-3 w-3" />
                <span>Grounding Tokens</span>
              </div>
              <p className="font-semibold text-foreground mt-0.5">{allowlist.length} verified</p>
            </div>

            <div className="rounded-lg bg-muted/40 p-2 border border-border/40 col-span-2 sm:col-span-1">
              <div className="flex items-center space-x-1.5 text-muted-foreground text-[10px] uppercase font-mono">
                <Tag className="h-3 w-3" />
                <span>Kind</span>
              </div>
              <p className="font-semibold text-foreground mt-0.5 capitalize">{evidence.kind}</p>
            </div>
          </div>

          {allowlist.length > 0 && (
            <div>
              <div className="text-[10px] font-mono text-muted-foreground uppercase mb-1.5">
                Allowed Verifier Tokens ({allowlist.length})
              </div>
              <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto p-1.5 rounded-lg bg-muted/30 border border-border/40">
                {allowlist.map((tok, i) => (
                  <span
                    key={`${tok}-${i}`}
                    className="inline-flex items-center rounded bg-background px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground border border-border/50"
                  >
                    {tok}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              onClick={() => setShowJson(!showJson)}
              className="inline-flex items-center space-x-1 text-[11px] text-primary hover:underline font-mono"
            >
              <Terminal className="h-3 w-3" />
              <span>{showJson ? 'Hide Raw JSON' : 'Inspect Raw Envelope JSON'}</span>
            </button>
          </div>

          {showJson && (
            <pre className="rounded-lg bg-black/80 text-emerald-400 p-2.5 text-[11px] font-mono overflow-x-auto max-h-48 border border-border/80">
              {JSON.stringify(evidence, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};
