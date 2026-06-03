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

export type AgentProvider = 'google' | 'anthropic' | 'deepseek' | 'openrouter' | 'nvidia_nim';

interface ProviderOption {
  id: AgentProvider;
  label: string;
  models: string[];
}

export const PROVIDER_OPTIONS: ProviderOption[] = [
  { id: 'google', label: 'Google Gemini', models: ['gemini-3.5-flash', 'gemini-2.5-pro'] },
  { id: 'anthropic', label: 'Anthropic', models: ['claude-sonnet-4-20250514', 'claude-3-5-haiku-20241022'] },
  { id: 'deepseek', label: 'DeepSeek', models: ['deepseek-chat', 'deepseek-reasoner'] },
  { id: 'openrouter', label: 'OpenRouter', models: ['openrouter/auto', 'meta-llama/llama-4-maverick'] },
  { id: 'nvidia_nim', label: 'NVIDIA NIM', models: ['nvidia/llama-3.1-nemotron-70b-instruct'] },
];

interface AgentState {
  // Chat
  messages: ChatMessage[];
  thoughts: ThoughtEntry[];
  isStreaming: boolean;

  // Provider config
  provider: AgentProvider;
  model: string;

  // UI state
  sidebarOpen: boolean;
  consoleOpen: boolean;
  consoleHeight: number; // px

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
  clearChat: () => void;
  clearThoughts: () => void;

  // Async action: send message and process SSE
  sendMessage: (text: string) => Promise<void>;
  uploadFile: (file: File) => Promise<string | null>;
}

let idCounter = 0;
const uid = () => `msg_${Date.now()}_${++idCounter}`;

const API_BASE = '/api/agent';

export const useAgentStore = create<AgentState>()((set, get) => ({
  messages: [],
  thoughts: [],
  isStreaming: false,

  provider: 'google',
  model: 'gemini-3.5-flash',

  sidebarOpen: true,
  consoleOpen: false,
  consoleHeight: 220,

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
    set({ provider, model: opt?.models[0] || '' });
  },
  setModel: (model) => set({ model }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setConsoleOpen: (open) => set({ consoleOpen: open }),
  setConsoleHeight: (height) => set({ consoleHeight: Math.max(120, Math.min(500, height)) }),
  clearChat: () => set({ messages: [] }),
  clearThoughts: () => set({ thoughts: [] }),

  sendMessage: async (text: string) => {
    const { provider, model, addMessage, appendToLastAssistant, addThought, setStreaming } = get();

    // Add user message
    addMessage({ id: uid(), role: 'user', content: text, timestamp: Date.now() });

    // Create placeholder assistant message
    const assistantId = uid();
    addMessage({ id: assistantId, role: 'assistant', content: '', timestamp: Date.now() });

    setStreaming(true);

    // Open console when streaming starts (to show thoughts)
    set({ consoleOpen: true });

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, provider, model }),
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

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          if (trimmed.startsWith('THOUGHT: ')) {
            const thought = trimmed.slice('THOUGHT: '.length);
            addThought({ id: uid(), content: thought, timestamp: Date.now() });
          } else if (trimmed.startsWith('TEXT: ')) {
            const token = trimmed.slice('TEXT: '.length);
            appendToLastAssistant(token);
          }
        }
      }

      // Process any remaining buffer
      if (buffer.trim()) {
        const trimmed = buffer.trim();
        if (trimmed.startsWith('THOUGHT: ')) {
          addThought({ id: uid(), content: trimmed.slice('THOUGHT: '.length), timestamp: Date.now() });
        } else if (trimmed.startsWith('TEXT: ')) {
          appendToLastAssistant(trimmed.slice('TEXT: '.length));
        }
      }
    } catch (err) {
      appendToLastAssistant(`\nConnection error: ${err instanceof Error ? err.message : String(err)}`);
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
