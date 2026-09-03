import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

export interface ThoughtEntry {
  id: string;
  content: string;
  timestamp: number;
}

export type AgentProvider =
  | 'google'
  | 'anthropic'
  | 'deepseek'
  | 'openrouter'
  | 'nvidia_nim';

export interface ModelInfo {
  id: string;
  label: string;
  description: string;
  tier: 'flagship' | 'fast' | 'balanced';
}

export interface ProviderOption {
  id: AgentProvider;
  label: string;
  icon: string;
  models: ModelInfo[];
}

// ── Latest mid-2026 model roster ──────────────────────────────────────────
export const PROVIDER_OPTIONS: ProviderOption[] = [
  {
    id: 'google',
    label: 'Google Gemini',
    icon: 'auto_awesome',
    models: [
      {
        id: 'gemini-3.5-flash',
        label: 'Gemini 3.5 Flash',
        description: 'Fast & agentic. Ideal for tool-use workflows.',
        tier: 'fast',
      },
      {
        id: 'gemini-3.1-pro-preview',
        label: 'Gemini 3.1 Pro Preview',
        description: 'Frontier reasoning & advanced multi-step planning.',
        tier: 'flagship',
      },
    ],
  },
  {
    id: 'anthropic',
    label: 'Anthropic Claude',
    icon: 'psychology',
    models: [
      {
        id: 'claude-opus-4-8',
        label: 'Claude Opus 4.8',
        description: 'Flagship. 1M context, adaptive thinking, agentic coding.',
        tier: 'flagship',
      },
      {
        id: 'claude-3-5-haiku-20241022',
        label: 'Claude 3.5 Haiku',
        description: 'Speed-optimised. Best for real-time tool interactions.',
        tier: 'fast',
      },
    ],
  },
  {
    id: 'deepseek',
    label: 'DeepSeek',
    icon: 'search',
    models: [
      {
        id: 'deepseek-v4-pro',
        label: 'DeepSeek V4 Pro',
        description: 'Flagship MoE (1.6T params). Strong STEM & reasoning.',
        tier: 'flagship',
      },
      {
        id: 'deepseek-v4-flash',
        label: 'DeepSeek V4 Flash',
        description: 'Cost-efficient variant with thinking mode support.',
        tier: 'fast',
      },
    ],
  },
  {
    id: 'openrouter',
    label: 'OpenRouter',
    icon: 'hub',
    models: [
      {
        id: 'openrouter/auto',
        label: 'Auto (Best Available)',
        description: 'OpenRouter selects the optimal model automatically.',
        tier: 'balanced',
      },
      {
        id: 'meta-llama/llama-4-maverick',
        label: 'Llama 4 Maverick',
        description: 'Meta open-weights model via OpenRouter.',
        tier: 'balanced',
      },
      {
        id: 'anthropic/claude-opus-4-8',
        label: 'Claude Opus 4.8 (via OR)',
        description: 'Anthropic flagship routed through OpenRouter.',
        tier: 'flagship',
      },
    ],
  },
  {
    id: 'nvidia_nim',
    label: 'NVIDIA NIM',
    icon: 'memory',
    models: [
      {
        id: 'nvidia/llama-3.1-nemotron-70b-instruct',
        label: 'Nemotron 70B',
        description: 'GPU-optimised instruction model via NVIDIA NIM.',
        tier: 'balanced',
      },
    ],
  },
];

export type ProviderKeysStatus = Record<AgentProvider, boolean | null>;

interface AgentState {
  // Chat
  messages: ChatMessage[];
  thoughts: ThoughtEntry[];
  isStreaming: boolean;

  // Provider config
  provider: AgentProvider;
  model: string;

  // Provider key status (null = not yet fetched)
  providerKeysStatus: ProviderKeysStatus;
  keysStatusLoaded: boolean;

  // UI state
  sidebarOpen: boolean;
  consoleOpen: boolean;
  consoleHeight: number;

  // Dynamic UI builder state
  generatedUiSpec: any | null;
  uploadedDataset: any[] | null;
  hasNewUiNotification: boolean;

  // Actions
  addMessage: (msg: ChatMessage) => void;
  appendToLastAssistant: (text: string) => void;
  addThought: (thought: ThoughtEntry) => void;
  setStreaming: (streaming: boolean) => void;
  setProvider: (provider: AgentProvider) => void;
  setModel: (model: string) => void;
  setSidebarOpen: (open: boolean) => void;
  setConsoleOpen: (open: boolean) => void;
  setConsoleHeight: (height: number) => void;
  setGeneratedUiSpec: (spec: any) => void;
  setUploadedDataset: (data: any[]) => void;
  setHasNewUiNotification: (notif: boolean) => void;
  clearChat: () => void;
  clearThoughts: () => void;
  fetchKeysStatus: () => Promise<void>;

  // Async actions
  sendMessage: (text: string) => Promise<void>;
  uploadFile: (file: File) => Promise<string | null>;
}

let idCounter = 0;
const uid = () => `msg_${Date.now()}_${++idCounter}`;

const API_BASE = '/api/agent';

const DEFAULT_KEYS_STATUS: ProviderKeysStatus = {
  google: null,
  anthropic: null,
  deepseek: null,
  openrouter: null,
  nvidia_nim: null,
};

export const useAgentStore = create<AgentState>()((set, get) => ({
  messages: [],
  thoughts: [],
  isStreaming: false,

  provider: 'deepseek',
  model: 'deepseek-v4-flash',

  providerKeysStatus: DEFAULT_KEYS_STATUS,
  keysStatusLoaded: false,

  sidebarOpen: typeof window !== 'undefined' ? window.innerWidth >= 1024 : false,
  consoleOpen: false,
  consoleHeight: 220,

  generatedUiSpec: null,
  uploadedDataset: null,
  hasNewUiNotification: false,

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  appendToLastAssistant: (text) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, content: last.content + text };
      }
      return { messages: msgs };
    }),
  addThought: (thought) => set((s) => ({ thoughts: [...s.thoughts, thought] })),
  setStreaming: (streaming) => set({ isStreaming: streaming }),
  setProvider: (provider) => {
    const opt = PROVIDER_OPTIONS.find((p) => p.id === provider);
    set({ provider, model: opt?.models[0]?.id || '' });
  },
  setModel: (model) => set({ model }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setConsoleOpen: (open) => set({ consoleOpen: open }),
  setConsoleHeight: (height) =>
    set({ consoleHeight: Math.max(120, Math.min(500, height)) }),
  setGeneratedUiSpec: (generatedUiSpec) => set({ generatedUiSpec }),
  setUploadedDataset: (uploadedDataset) => set({ uploadedDataset }),
  setHasNewUiNotification: (hasNewUiNotification) => set({ hasNewUiNotification }),
  clearChat: () => set({ messages: [], thoughts: [], generatedUiSpec: null, uploadedDataset: null, hasNewUiNotification: false }),
  clearThoughts: () => set({ thoughts: [] }),

  fetchKeysStatus: async () => {
    try {
      const res = await fetch(`${API_BASE}/providers/status`);
      if (!res.ok) return;
      const data = await res.json();
      set({ providerKeysStatus: { ...DEFAULT_KEYS_STATUS, ...data }, keysStatusLoaded: true });
    } catch {
      // silently ignore — will show null (unknown) in UI
    }
  },

  sendMessage: async (text: string) => {
    const {
      provider,
      model,
      messages,
      addMessage,
      appendToLastAssistant,
      addThought,
      setStreaming,
    } = get();

    addMessage({ id: uid(), role: 'user', content: text, timestamp: Date.now() });

    const assistantId = uid();
    addMessage({ id: assistantId, role: 'assistant', content: '', timestamp: Date.now() });

    setStreaming(true);
    set({ consoleOpen: true });

    // Build history from existing messages (exclude the just-added placeholder)
    const history = messages
      .filter((m) => m.content !== '')
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, provider, model, history }),
      });

      if (!res.ok) {
        appendToLastAssistant(`Error: ${res.status} ${res.statusText}`);
        setStreaming(false);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        appendToLastAssistant('Error: No response stream');
        setStreaming(false);
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line) continue;

          if (line.startsWith('THOUGHT:')) {
            try {
              const content = JSON.parse(line.slice('THOUGHT:'.length));
              addThought({
                id: uid(),
                content: content,
                timestamp: Date.now(),
              });
            } catch (err) {
              console.error('Error parsing THOUGHT JSON:', err, line);
            }
          } else if (line.startsWith('TEXT:')) {
            try {
              const content = JSON.parse(line.slice('TEXT:'.length));
              appendToLastAssistant(content);
            } catch (err) {
              console.error('Error parsing TEXT JSON:', err, line);
            }
          } else if (line.startsWith('UI_SPEC:')) {
            try {
              const specData = JSON.parse(line.slice('UI_SPEC:'.length));
              const { file_path, config } = specData;
              set({ generatedUiSpec: config, hasNewUiNotification: true });
              
              fetch(`${API_BASE}/data?file_path=${encodeURIComponent(file_path)}`)
                .then(res => {
                  if (res.ok) return res.json();
                  throw new Error('Failed to load dataset');
                })
                .then(dataset => {
                  set({ uploadedDataset: dataset });
                })
                .catch(err => {
                  console.error('Error loading dynamic dataset:', err);
                });
            } catch (err) {
              console.error('Error parsing UI_SPEC JSON:', err, line);
            }
          }
        }
      }

      // Flush remaining buffer
      if (buffer) {
        const line = buffer;
        if (line.startsWith('THOUGHT:')) {
          try {
            const content = JSON.parse(line.slice('THOUGHT:'.length));
            addThought({
              id: uid(),
              content: content,
              timestamp: Date.now(),
            });
          } catch (err) {
            console.error('Error parsing THOUGHT JSON (flush):', err, line);
          }
        } else if (line.startsWith('TEXT:')) {
          try {
            const content = JSON.parse(line.slice('TEXT:'.length));
            appendToLastAssistant(content);
          } catch (err) {
            console.error('Error parsing TEXT JSON (flush):', err, line);
          }
        } else if (line.startsWith('UI_SPEC:')) {
          try {
            const specData = JSON.parse(line.slice('UI_SPEC:'.length));
            const { file_path, config } = specData;
            set({ generatedUiSpec: config, hasNewUiNotification: true });
            
            fetch(`${API_BASE}/data?file_path=${encodeURIComponent(file_path)}`)
              .then(res => {
                if (res.ok) return res.json();
                throw new Error('Failed to load dataset');
              })
              .then(dataset => {
                set({ uploadedDataset: dataset });
              })
              .catch(err => {
                console.error('Error loading dynamic dataset:', err);
              });
          } catch (err) {
            console.error('Error parsing UI_SPEC JSON (flush):', err, line);
          }
        }
      }
    } catch (err) {
      appendToLastAssistant(
        `\nConnection error: ${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      setStreaming(false);
    }
  },

  uploadFile: async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
      if (!res.ok) return null;
      const data = await res.json();
      return data.file_path || null;
    } catch {
      return null;
    }
  },
}));
