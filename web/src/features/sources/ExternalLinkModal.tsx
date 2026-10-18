import React from 'react';
import { ExternalLink, ShieldAlert, X } from 'lucide-react';

interface ExternalLinkModalProps {
  isOpen: boolean;
  url: string | null;
  domain?: string;
  onClose: () => void;
}

export const ExternalLinkModal: React.FC<ExternalLinkModalProps> = ({
  isOpen,
  url,
  domain,
  onClose,
}) => {
  if (!isOpen || !url) return null;

  const handleConfirm = () => {
    window.open(url, '_blank', 'noopener,noreferrer');
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-150"
    >
      <div className="relative w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl text-card-foreground">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold">External Link Safety Warning</h3>
            <p className="text-xs text-muted-foreground">Navigating away from Warrant X-Ray</p>
          </div>
        </div>

        <p className="text-xs text-muted-foreground mb-3 leading-relaxed">
          You are about to visit an external third-party news publication{' '}
          {domain && <span className="font-semibold text-foreground">({domain})</span>}.
          Warrant X-Ray verifies article citations and stated numbers, but third-party domains may contain unverified opinions or speculative commentary.
        </p>

        <div className="rounded-lg bg-muted/60 p-2.5 text-[11px] font-mono text-muted-foreground break-all border border-border/50 mb-5">
          {url}
        </div>

        <div className="flex items-center justify-end space-x-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-1.5 text-xs font-medium rounded-lg border border-border bg-background hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs"
          >
            <span>Continue to External Site</span>
            <ExternalLink className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  );
};
