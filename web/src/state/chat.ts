import { create } from 'zustand';
import { streamChat, type ViewLinkData } from '../api/sse';
import type { WarrantCardData } from '../features/card/types';
import type { ToolTraceItem } from '../features/chat/ToolTrace';

export interface EvidenceItem {
  evidence_id: string;
  kind: string;
  source: string;
  as_of: string;
  summary: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isPartial?: boolean;
  isVerified?: boolean;
  links?: ViewLinkData[];
}

export interface ChatState {
  sessionId: string;
  messages: ChatMessage[];
  isStreaming: boolean;
  activeTraces: ToolTraceItem[];
  evidenceMap: Record<string, EvidenceItem>;
  activeCard: WarrantCardData | null;
  selectedEvidenceId: string | null;
  error: string | null;

  // Actions
  sendMessage: (text: string) => Promise<void>;
  cancelStream: () => void;
  setSelectedEvidenceId: (id: string | null) => void;
  setActiveCard: (card: WarrantCardData | null) => void;
  clearMessages: () => void;
}

function getOrCreateSessionId(): string {
  try {
    const existing = sessionStorage.getItem('wx_session_id');
    if (existing) return existing;
    const newId = `sess_${Math.random().toString(36).substring(2, 11)}_${Date.now()}`;
    sessionStorage.setItem('wx_session_id', newId);
    return newId;
  } catch {
    return `sess_${Math.random().toString(36).substring(2, 11)}_${Date.now()}`;
  }
}

let activeAbortController: AbortController | null = null;

export const useChatStore = create<ChatState>((set, get) => ({
  sessionId: getOrCreateSessionId(),
  messages: [],
  isStreaming: false,
  activeTraces: [],
  evidenceMap: {},
  activeCard: null,
  selectedEvidenceId: null,
  error: null,

  setSelectedEvidenceId: (id) => set({ selectedEvidenceId: id }),
  setActiveCard: (card) => set({ activeCard: card }),
  clearMessages: () => set({ messages: [], activeTraces: [], error: null }),

  cancelStream: () => {
    if (activeAbortController) {
      activeAbortController.abort();
      activeAbortController = null;
    }
    set({ isStreaming: false });
  },

  sendMessage: async (text: string) => {
    const { sessionId, isStreaming } = get();
    if (isStreaming || !text.trim()) return;

    if (activeAbortController) {
      activeAbortController.abort();
    }
    const abortController = new AbortController();
    activeAbortController = abortController;

    const userMsgId = `user_${Date.now()}`;
    const assistantMsgId = `asst_${Date.now()}`;

    set((state) => ({
      isStreaming: true,
      error: null,
      activeTraces: [],
      messages: [
        ...state.messages,
        { id: userMsgId, role: 'user', content: text },
        { id: assistantMsgId, role: 'assistant', content: '', isVerified: true },
      ],
    }));

    try {
      await streamChat(
        {
          session_id: sessionId,
          message: text,
          mode: 'chat',
        },
        {
          onStatus: (status) => {
            set((state) => ({
              activeTraces: [
                ...state.activeTraces,
                { name: `step_${status.step}`, text: status.text, step: status.step },
              ],
            }));
          },
          onToolCall: (tc) => {
            set((state) => ({
              activeTraces: [
                ...state.activeTraces,
                { name: tc.name, text: `Executing ${tc.name}...` },
              ],
            }));
          },
          onEvidence: (ev) => {
            set((state) => ({
              evidenceMap: { ...state.evidenceMap, [ev.evidence_id]: ev },
            }));
          },
          onCard: (_card) => {
            // Calculation figures provided via deep links; ignore raw card event
          },
          onLinks: (data) => {
            set((state) => {
              const msgs = [...state.messages];
              const lastIdx = msgs.length - 1;
              if (lastIdx >= 0 && msgs[lastIdx].role === 'assistant') {
                msgs[lastIdx] = {
                  ...msgs[lastIdx],
                  links: data.links,
                };
              }
              return { messages: msgs };
            });
          },
          onToken: (tok) => {
            set((state) => {
              const msgs = [...state.messages];
              const lastIdx = msgs.length - 1;
              if (lastIdx >= 0 && msgs[lastIdx].role === 'assistant') {
                msgs[lastIdx] = {
                  ...msgs[lastIdx],
                  content: msgs[lastIdx].content + tok.text,
                };
              }
              return { messages: msgs };
            });
          },
          onVerifier: (vf) => {
            set((state) => {
              const msgs = [...state.messages];
              const lastIdx = msgs.length - 1;
              if (lastIdx >= 0 && msgs[lastIdx].role === 'assistant') {
                msgs[lastIdx] = {
                  ...msgs[lastIdx],
                  isVerified: vf.passed,
                };
              }
              return { messages: msgs };
            });
          },
          onError: (err) => {
            set((state) => {
              const msgs = [...state.messages];
              const lastIdx = msgs.length - 1;
              if (lastIdx >= 0 && msgs[lastIdx].role === 'assistant') {
                msgs[lastIdx] = {
                  ...msgs[lastIdx],
                  isPartial: true,
                };
              }
              return { error: err.message, isStreaming: false };
            });
          },
          onDone: () => {
            set({ isStreaming: false });
          },
        },
        abortController.signal
      );
    } catch (err: unknown) {
      if (!abortController.signal.aborted) {
        set({
          isStreaming: false,
          error: err instanceof Error ? err.message : 'Error communicating with server',
        });
      }
    } finally {
      if (activeAbortController === abortController) {
        activeAbortController = null;
      }
      set({ isStreaming: false });
    }
  },
}));
