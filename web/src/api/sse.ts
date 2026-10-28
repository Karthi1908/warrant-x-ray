import { fetchEventSource } from '@microsoft/fetch-event-source';
import type { WarrantCardData } from '../features/card/types';

export interface ChatRequest {
  session_id: string;
  message: string;
  mode?: 'chat' | 'deep';
  snapshot_id?: number | null;
}

export type LinkKind = 'card' | 'scenario' | 'compare' | 'stock' | 'sources' | 'health' | 'news';

export interface ViewLinkData {
  kind: LinkKind;
  label: string;
  href: string;
  entity?: {
    code?: string;
    ticker?: string;
    codes?: string[];
  };
  evidence_id?: string;
  retrieved_at?: string | null;
}

export interface ChatSseCallbacks {
  onTurnStarted?: (data: { turn_id: string }) => void;
  onStatus?: (data: { step: number; text: string }) => void;
  onToolCall?: (data: { name: string; args: Record<string, unknown> }) => void;
  onEvidence?: (data: {
    evidence_id: string;
    kind: string;
    source: string;
    as_of: string;
    summary: string;
  }) => void;
  onCard?: (card: WarrantCardData) => void;
  onToken?: (data: { text: string }) => void;
  onVerifier?: (data: { passed: boolean; retried: boolean; removed_sentences: number }) => void;
  onLinks?: (data: { links: ViewLinkData[] }) => void;
  onUsage?: (data: {
    model: string;
    tier: string;
    in_tokens: number;
    out_tokens: number;
    latency_ms: number;
    cost_usd: number;
  }) => void;
  onDone?: (data: { turn_id: string }) => void;
  onError?: (error: { code?: string; message: string; recoverable?: boolean }) => void;
}

export class FatalStreamError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'FatalStreamError';
  }
}

export async function streamChat(
  req: ChatRequest,
  callbacks: ChatSseCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const url = '/api/chat';

  await fetchEventSource(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
      'X-Session-ID': req.session_id,
    },
    body: JSON.stringify(req),
    signal,
    openWhenHidden: true,
    async onopen(response) {
      if (response.ok && response.headers.get('content-type')?.includes('text/event-stream')) {
        return; // everything is good
      } else if (response.status >= 400 && response.status < 500 && response.status !== 429) {
        // client-side errors are usually fatal
        const errText = await response.text();
        throw new FatalStreamError(`Client error ${response.status}: ${errText}`);
      } else {
        throw new Error(`Server error ${response.status}`);
      }
    },
    onmessage(msg) {
      if (!msg.event || msg.event === '') return;
      try {
        const parsed = msg.data ? JSON.parse(msg.data) : {};
        switch (msg.event) {
          case 'turn_started':
            callbacks.onTurnStarted?.(parsed);
            break;
          case 'status':
            callbacks.onStatus?.(parsed);
            break;
          case 'tool_call':
            callbacks.onToolCall?.(parsed);
            break;
          case 'evidence':
            callbacks.onEvidence?.(parsed);
            break;
          case 'card':
            callbacks.onCard?.(parsed);
            break;
          case 'token':
            callbacks.onToken?.(parsed);
            break;
          case 'verifier':
            callbacks.onVerifier?.(parsed);
            break;
          case 'links':
            callbacks.onLinks?.(parsed);
            break;
          case 'usage':
            callbacks.onUsage?.(parsed);
            break;
          case 'done':
            callbacks.onDone?.(parsed);
            break;
          case 'error':
            callbacks.onError?.(parsed);
            break;
          default:
            break;
        }
      } catch (err) {
        console.error('Failed to parse SSE event payload', msg.event, err);
      }
    },
    onclose() {
      // Normal close
    },
    onerror(err) {
      if (signal?.aborted) return;
      callbacks.onError?.({
        message: err instanceof Error ? err.message : 'Chat stream disconnected',
        recoverable: true,
      });
      // Return undefined or rethrow to stop retries if fatal
      if (err instanceof FatalStreamError) {
        throw err;
      }
    },
  });
}
