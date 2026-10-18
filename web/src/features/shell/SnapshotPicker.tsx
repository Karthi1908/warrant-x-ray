import React, { useEffect, useState } from 'react';
import { cn } from '../../lib/utils';
import { History, Check, ChevronDown } from 'lucide-react';

export interface SnapshotItem {
  id: number;
  fetched_at: string;
  row_count?: number;
  ok?: boolean;
  note?: string;
}

export interface SnapshotPickerProps {
  selectedSnapshotId?: number | null;
  onSelectSnapshot?: (id: number | null) => void;
  className?: string;
}

export const SnapshotPicker: React.FC<SnapshotPickerProps> = ({
  selectedSnapshotId,
  onSelectSnapshot,
  className,
}) => {
  const [snapshots, setSnapshots] = useState<SnapshotItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    let mounted = true;
    const fetchSnapshots = async () => {
      setLoading(true);
      try {
        const resp = await fetch('/api/snapshots');
        if (resp.ok) {
          const data = await resp.json();
          if (mounted && Array.isArray(data.snapshots)) {
            setSnapshots(data.snapshots);
          }
        }
      } catch {
        // Fallback gracefully if offline
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchSnapshots();
    return () => {
      mounted = false;
    };
  }, [isOpen]);

  const formatSnapshotTime = (iso: string) => {
    try {
      const d = new Date(iso);
      return (
        d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
        ' ' +
        d.toLocaleDateString([], { month: 'short', day: 'numeric' })
      );
    } catch {
      return iso;
    }
  };

  const selectedItem = snapshots.find((s) => s.id === selectedSnapshotId);

  return (
    <div className={cn('relative inline-block text-left', className)}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center space-x-1.5 rounded-lg border border-border bg-card/60 px-2.5 py-1 text-xs font-medium text-foreground hover:bg-muted/60 transition-colors"
        title="Pin market data to a specific historical snapshot"
      >
        <History className="h-3.5 w-3.5 text-muted-foreground" />
        <span>
          {selectedSnapshotId
            ? `Snap #${selectedSnapshotId} (${selectedItem ? formatSnapshotTime(selectedItem.fetched_at) : 'Pinned'})`
            : 'Latest Data'}
        </span>
        <ChevronDown className="h-3 w-3 text-muted-foreground opacity-70" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-1.5 w-64 rounded-xl border border-border bg-popover p-1.5 text-popover-foreground shadow-xl z-50">
          <div className="px-2 py-1 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
            Market Snapshots
          </div>
          <div className="max-h-60 overflow-y-auto space-y-0.5 mt-1">
            <button
              type="button"
              onClick={() => {
                onSelectSnapshot?.(null);
                setIsOpen(false);
              }}
              className={cn(
                'w-full flex items-center justify-between rounded-md px-2 py-1.5 text-xs text-left hover:bg-muted transition-colors',
                !selectedSnapshotId && 'bg-primary/10 text-primary font-medium'
              )}
            >
              <span>Latest (Dynamic)</span>
              {!selectedSnapshotId && <Check className="h-3.5 w-3.5" />}
            </button>

            {loading && snapshots.length === 0 && (
              <div className="px-2 py-2 text-xs text-muted-foreground">Loading snapshots...</div>
            )}

            {snapshots.map((snap) => (
              <button
                key={snap.id}
                type="button"
                onClick={() => {
                  onSelectSnapshot?.(snap.id);
                  setIsOpen(false);
                }}
                className={cn(
                  'w-full flex items-center justify-between rounded-md px-2 py-1.5 text-xs text-left hover:bg-muted transition-colors',
                  selectedSnapshotId === snap.id && 'bg-primary/10 text-primary font-medium'
                )}
              >
                <div>
                  <div className="font-mono text-[11px]">Snapshot #{snap.id}</div>
                  <div className="text-[10px] text-muted-foreground">
                    {formatSnapshotTime(snap.fetched_at)}
                  </div>
                </div>
                {selectedSnapshotId === snap.id && <Check className="h-3.5 w-3.5 shrink-0" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
