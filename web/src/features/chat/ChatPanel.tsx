import React from 'react';
import { cn } from '../../lib/utils';
import { useChatStore } from '../../state/chat';
import { MessageList } from './MessageList';
import { ToolTrace } from './ToolTrace';
import { SamplePrompts } from './SamplePrompts';
import { Composer } from './Composer';
import { Trash2, AlertCircle, X } from 'lucide-react';

import type { ViewLinkData } from '../../api/sse';

export interface ChatPanelProps {
  onLinkClick?: (href: string, link: ViewLinkData) => void;
  className?: string;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ onLinkClick, className }) => {
  const {
    messages,
    isStreaming,
    activeTraces,
    error,
    evidenceMap,
    selectedEvidenceId,
    sendMessage,
    cancelStream,
    clearMessages,
    setSelectedEvidenceId,
  } = useChatStore();

  const selectedEvidence = selectedEvidenceId ? evidenceMap[selectedEvidenceId] : null;

  return (
    <div
      className={cn(
        'flex flex-col h-full bg-card border-2 border-border rounded-xl shadow-xs overflow-hidden',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b-2 border-border px-4 py-3 bg-muted/40">
        <div>
          <h2 className="text-sm font-bold tracking-tight text-foreground">Risk Copilot Chat</h2>
          <p className="text-[11px] text-muted-foreground font-semibold">
            Grounded answers with deterministic numbers & citations
          </p>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={clearMessages}
            disabled={isStreaming}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted transition-colors disabled:opacity-40"
            title="Clear conversation"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Selected Evidence Detail Modal / Drawer */}
      {selectedEvidence && (
        <div className="bg-primary/5 border-b border-primary/20 px-4 py-2.5 flex items-start justify-between text-xs">
          <div className="space-y-1 pr-2">
            <div className="flex items-center space-x-2 font-mono font-medium text-primary">
              <span>[{selectedEvidence.evidence_id}]</span>
              <span className="text-foreground/70">{selectedEvidence.kind}</span>
              <span className="text-muted-foreground text-[10px]">({selectedEvidence.as_of})</span>
            </div>
            <p className="text-foreground/90">{selectedEvidence.summary}</p>
            <div className="text-[10px] text-muted-foreground truncate">
              Source: {selectedEvidence.source}
            </div>
          </div>
          <button
            type="button"
            onClick={() => setSelectedEvidenceId(null)}
            className="text-muted-foreground hover:text-foreground p-1"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Messages */}
      <MessageList
        messages={messages}
        onCitationClick={(id) => setSelectedEvidenceId(id)}
        onLinkClick={onLinkClick}
        className="flex-1 min-h-0"
      />

      {/* Tool Trace Activity */}
      {isStreaming && activeTraces.length > 0 && (
        <div className="px-4">
          <ToolTrace traces={activeTraces} />
        </div>
      )}

      {/* Error notification */}
      {error && (
        <div className="mx-4 my-2 flex items-center space-x-2 rounded-lg bg-destructive/10 border border-destructive/20 p-2.5 text-xs text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Bottom Area: Sample Prompts & Composer */}
      <div className="border-t-2 border-border p-3 space-y-2.5 bg-background">
        {messages.length === 0 && (
          <SamplePrompts onSelect={(prompt) => sendMessage(prompt)} />
        )}
        <Composer
          onSend={(text) => sendMessage(text)}
          isStreaming={isStreaming}
          onCancel={cancelStream}
        />
      </div>
    </div>
  );
};
