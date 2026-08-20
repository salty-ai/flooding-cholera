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
        id: 'deepseek-v4-flash',
        label: 'DeepSeek V4 Flash',
        description: 'Ultra-fast inference & reasoning.',
        tier: 'fast',
      },
    ],
  },
  {
    id: 'nvidia_nim',
    label: 'NVIDIA NIM',
    icon: 'memory',
    models: [
      {
        id: 'meta/llama-3.3-70b-instruct',
        label: 'Llama 3.3 70B (NIM)',
        description: 'Hosted on NVIDIA NIM infrastructure.',
        tier: 'flagship',
      },
    ],
  },
  {
    id: 'openrouter',
    label: 'OpenRouter',
    icon: 'alt_route',
    models: [
      {
        id: 'auto',
        label: 'Auto Router',
        description: 'Dynamically routes to optimal active model.',
        tier: 'balanced',
      },
    ],
  },
];

const DEFAULT_KEYS_STATUS: Record<AgentProvider, boolean | null> = {
  google: true,
  anthropic: true,
  deepseek: true,
  nvidia_nim: true,
  openrouter: true,
};

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

interface AgentStore {
  messages: ChatMessage[];
  thoughts: ThoughtEntry[];
  isStreaming: boolean;

  provider: AgentProvider;
  model: string;

  providerKeysStatus: Record<AgentProvider, boolean | null>;
  keysStatusLoaded: boolean;

  sidebarOpen: boolean;
  consoleOpen: boolean;
  consoleHeight: number;

  generatedUiSpec: any | null;
  uploadedDataset: any[] | null;
  hasNewUiNotification: boolean;

  addMessage: (msg: ChatMessage) => void;
  appendToLastAssistant: (text: string) => void;
  addThought: (thought: ThoughtEntry) => void;
  setStreaming: (streaming: boolean) => void;
  setProvider: (provider: AgentProvider) => void;
  setModel: (model: string) => void;
  setSidebarOpen: (open: boolean) => void;
  setConsoleOpen: (open: boolean) => void;
  setConsoleHeight: (height: number) => void;
  setGeneratedUiSpec: (spec: unknown) => void;
  setUploadedDataset: (dataset: any[]) => void;
  setHasNewUiNotification: (flag: boolean) => void;
  clearChat: () => void;
  clearThoughts: () => void;
  fetchKeysStatus: () => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
  uploadFile: (file: File) => Promise<string | null>;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  messages: [],
  thoughts: [],
  isStreaming: false,

  provider: 'google',
  model: 'gemini-3.5-flash',

  providerKeysStatus: DEFAULT_KEYS_STATUS,
  keysStatusLoaded: false,

  // Default to closed on mobile viewports (<768px), open on desktop (>=768px)
  sidebarOpen: typeof window !== 'undefined' ? window.innerWidth >= 768 : false,
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
  clearChat: () =>
    set({
      messages: [],
      thoughts: [],
      generatedUiSpec: null,
      uploadedDataset: null,
      hasNewUiNotification: false,
    }),
  clearThoughts: () => set({ thoughts: [] }),

  fetchKeysStatus: async () => {
    try {
      const res = await fetch(`${API_BASE}/providers/status`);
      if (!res.ok) return;
      const data = await res.json();
      set({ providerKeysStatus: { ...DEFAULT_KEYS_STATUS, ...data }, keysStatusLoaded: true });
    } catch {
      // ignore
    }
  },

  sendMessage: async (text: string) => {
    const { provider, model, messages, addMessage, setStreaming, appendToLastAssistant, fetchKeysStatus } = get();

    if (!text.trim()) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };
    addMessage(userMsg);

    const assistantMsg: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    };
    addMessage(assistantMsg);

    setStreaming(true);

    try {
      await fetchKeysStatus();
      const res = await fetch(`${API_BASE}/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          model,
          messages: [...messages, userMsg].map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      if (!res.ok) {
        throw new Error(`API returned ${res.status}`);
      }

      const data = await res.json();
      appendToLastAssistant(data.reply || 'Analysis complete.');
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      appendToLastAssistant(`Sorry, an error occurred: ${errMsg}`);
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
