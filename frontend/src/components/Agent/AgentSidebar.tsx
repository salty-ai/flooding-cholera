import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { useAgentStore, PROVIDER_OPTIONS } from '../../store/agentStore';
import type { ProviderOption, ModelInfo } from '../../store/agentStore';

// ── Inline tool-use message card ──────────────────────────────────────────
function ToolCallCard({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);

  const isExec = content.startsWith('🔧');
  const isOutput = content.startsWith('📦');
  const isMock = content.startsWith('Mock');

  if (!isExec && !isOutput && !isMock) return null;

  const label = isExec
    ? 'Tool Executing'
    : isOutput
    ? 'Tool Output'
    : 'Mock Mode';
  const accentColor = isExec
    ? 'from-violet-500/20 to-purple-500/10 border-violet-400/30'
    : isOutput
    ? 'from-emerald-500/20 to-teal-500/10 border-emerald-400/30'
    : 'from-amber-500/20 to-orange-500/10 border-amber-400/30';
  const dotColor = isExec ? 'bg-violet-400' : isOutput ? 'bg-emerald-400' : 'bg-amber-400';
  const labelColor = isExec
    ? 'text-violet-300'
    : isOutput
    ? 'text-emerald-300'
    : 'text-amber-300';

  return (
    <div
      className={`my-1.5 rounded-lg border bg-gradient-to-r ${accentColor} px-3 py-2 text-[11px] font-mono cursor-pointer transition-all hover:opacity-90`}
      onClick={() => setExpanded((e) => !e)}
    >
      <div className="flex items-center gap-2">
        <span className={`size-1.5 rounded-full flex-shrink-0 ${dotColor}`} />
        <span className={`font-semibold ${labelColor} uppercase tracking-wider text-[9px]`}>
          {label}
        </span>
        <span className="text-white/40 ml-auto">
          {expanded ? '▲' : '▼'}
        </span>
      </div>
      {expanded && (
        <p className="mt-2 text-white/70 whitespace-pre-wrap break-all leading-relaxed">
          {content}
        </p>
      )}
    </div>
  );
}

// ── Markdown renderer ──────────────────────────────────────────────────────
function MarkdownRenderer({ content, isStreaming }: { content: string; isStreaming?: boolean }) {
  const blocks = useMemo(() => {
    const lines = content.split('\n');
    const result: React.ReactNode[] = [];
    let currentList: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeBlockLines: string[] = [];

    const parseInline = (text: string): React.ReactNode[] => {
      // Split by bold (**bold**) and inline code (`code`)
      const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
      return parts.map((part, index) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={index} className="font-bold text-[#0f172a]">{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith('`') && part.endsWith('`')) {
          return <code key={index} className="bg-slate-100 border border-slate-200 px-1 py-0.5 rounded font-mono text-[11px] text-red-600">{part.slice(1, -1)}</code>;
        }
        return part;
      });
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Code blocks
      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          result.push(
            <pre key={`code-${i}`} className="bg-slate-955 text-slate-200 p-3 rounded-xl font-mono text-[11px] overflow-x-auto my-2 border border-slate-800">
              <code>{codeBlockLines.join('\n')}</code>
            </pre>
          );
          codeBlockLines = [];
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
        }
        continue;
      }

      if (inCodeBlock) {
        codeBlockLines.push(line);
        continue;
      }

      // Tool logs and mock logs
      const isTool = line.startsWith('🔧') || line.startsWith('📦') || line.startsWith('Mock');
      if (isTool) {
        result.push(<ToolCallCard key={`tool-${i}`} content={line} />);
        continue;
      }

      // Headers
      if (line.startsWith('### ')) {
        result.push(<h5 key={i} className="text-xs font-bold text-[#1e293b] mt-3 mb-1.5 uppercase tracking-wider">{parseInline(line.slice(4))}</h5>);
        continue;
      }
      if (line.startsWith('## ')) {
        result.push(<h4 key={i} className="text-sm font-bold text-[#0f172a] mt-4 mb-2">{parseInline(line.slice(3))}</h4>);
        continue;
      }
      if (line.startsWith('# ')) {
        result.push(<h3 key={i} className="text-base font-bold text-[#0f172a] mt-5 mb-2.5">{parseInline(line.slice(2))}</h3>);
        continue;
      }

      // Bullet Lists
      if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        const text = line.trim().slice(2);
        currentList.push(
          <li key={i} className="ml-4 list-disc text-[12px] text-[#334155] leading-relaxed my-0.5">
            {parseInline(text)}
          </li>
        );
        const nextLine = lines[i + 1];
        if (!nextLine || (!nextLine.trim().startsWith('- ') && !nextLine.trim().startsWith('* '))) {
          result.push(<ul key={`ul-${i}`} className="my-2 space-y-0.5">{currentList}</ul>);
          currentList = [];
        }
        continue;
      }

      // Numbered Lists
      const numMatch = line.trim().match(/^(\d+)\.\s(.*)/);
      if (numMatch) {
        const text = numMatch[2];
        currentList.push(
          <li key={i} className="ml-4 list-decimal text-[12px] text-[#334155] leading-relaxed my-0.5">
            {parseInline(text)}
          </li>
        );
        const nextLine = lines[i + 1];
        const nextNumMatch = nextLine ? nextLine.trim().match(/^(\d+)\.\s.*/) : null;
        if (!nextLine || !nextNumMatch) {
          result.push(<ol key={`ol-${i}`} className="my-2 space-y-0.5">{currentList}</ol>);
          currentList = [];
        }
        continue;
      }

      // Normal paragraph
      if (line.trim()) {
        result.push(
          <p key={i} className="text-[13px] text-[#334155] leading-relaxed my-1.5 break-words font-medium">
            {parseInline(line)}
          </p>
        );
      } else {
        result.push(<div key={i} className="h-1" />);
      }
    }

    // Append streaming loading animation inside MarkdownRenderer if text is empty
    if (content === '' && isStreaming) {
      result.push(
        <div key="streaming-anim" className="flex items-center gap-1 py-1">
          <span className="size-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="size-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="size-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      );
    }

    return result;
  }, [content, isStreaming]);

  return <div className="space-y-1">{blocks}</div>;
}

// ── Message bubble ─────────────────────────────────────────────────────────
function MessageBubble({
  role,
  content,
  timestamp,
  isStreaming,
}: {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  isStreaming?: boolean;
}) {
  const timeStr = new Date(timestamp).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  });

  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-br from-primary to-blue-600 px-4 py-2.5 shadow-md shadow-primary/20">
          <p className="text-[13px] text-white leading-relaxed whitespace-pre-wrap break-words font-medium">
            {content}
          </p>
          <span className="block text-[9px] text-white/50 mt-1 text-right">{timeStr}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] space-y-0.5">
        {/* Header */}
        <div className="flex items-center gap-1.5 mb-1.5">
          <div className="size-5 rounded-md bg-gradient-to-br from-primary/30 to-blue-600/30 border border-primary/20 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-primary" style={{ fontSize: '12px' }}>
              smart_toy
            </span>
          </div>
          <span className="text-[10px] font-semibold text-[#637588]">Copilot</span>
          <span className="text-[9px] text-[#94a3b8] ml-1">{timeStr}</span>
        </div>

        <div className="bg-white border border-[#e6e8eb] rounded-2xl rounded-tl-md px-3.5 py-2.5 shadow-sm">
          <MarkdownRenderer content={content} isStreaming={isStreaming} />
        </div>
      </div>
    </div>
  );
}

// ── Tier badge ─────────────────────────────────────────────────────────────
function TierBadge({ tier }: { tier: ModelInfo['tier'] }) {
  const map = {
    flagship: 'bg-violet-100 text-violet-700 border-violet-200',
    fast: 'bg-sky-100 text-sky-700 border-sky-200',
    balanced: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  };
  return (
    <span
      className={`text-[9px] font-bold uppercase tracking-wider border rounded-full px-1.5 py-0.5 ${map[tier]}`}
    >
      {tier}
    </span>
  );
}

// ── Key status badge ────────────────────────────────────────────────────────
function KeyBadge({ active }: { active: boolean | null }) {
  if (active === null) return (
    <span className="text-[9px] text-[#94a3b8] font-mono">checking…</span>
  );
  return active ? (
    <span className="flex items-center gap-1 text-[9px] font-semibold text-emerald-600">
      <span className="size-1.5 rounded-full bg-emerald-500" />
      Active
    </span>
  ) : (
    <span className="flex items-center gap-1 text-[9px] font-semibold text-amber-600">
      <span className="size-1.5 rounded-full bg-amber-400" />
      Mock Mode
    </span>
  );
}

// ── Provider Selector Dropdown ─────────────────────────────────────────────
function ProviderSelector({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { provider, model, providerKeysStatus, setProvider, setModel } = useAgentStore();

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40" onClick={onClose} />
      {/* Panel */}
      <div className="absolute top-full left-0 right-0 mt-1.5 bg-white border border-[#e6e8eb] rounded-xl shadow-2xl z-50 overflow-hidden">
        {PROVIDER_OPTIONS.map((p: ProviderOption) => {
          const isActiveProvider = provider === p.id;
          const keyActive = providerKeysStatus[p.id];

          return (
            <div key={p.id}>
              {/* Provider header */}
              <div className="flex items-center justify-between px-3 py-2 bg-[#f8f9fb] border-b border-[#e6e8eb]">
                <div className="flex items-center gap-2">
                  <span
                    className="material-symbols-outlined text-[#637588]"
                    style={{ fontSize: '14px' }}
                  >
                    {p.icon}
                  </span>
                  <span className="text-[11px] font-bold text-[#374151] uppercase tracking-wide">
                    {p.label}
                  </span>
                </div>
                <KeyBadge active={keyActive} />
              </div>

              {/* Models list */}
              {p.models.map((m: ModelInfo) => {
                const isSelected = isActiveProvider && model === m.id;
                return (
                  <button
                    key={m.id}
                    onClick={() => {
                      setProvider(p.id);
                      setModel(m.id);
                      onClose();
                    }}
                    className={`w-full text-left px-3 py-2.5 transition-colors hover:bg-primary/5 flex items-start gap-2.5 border-b border-[#f0f2f5] last:border-0 ${
                      isSelected ? 'bg-primary/5' : ''
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span
                          className={`text-xs font-mono font-semibold ${
                            isSelected ? 'text-primary' : 'text-[#111518]'
                          }`}
                        >
                          {m.label}
                        </span>
                        <TierBadge tier={m.tier} />
                      </div>
                      <p className="text-[10px] text-[#637588] mt-0.5 leading-snug">
                        {m.description}
                      </p>
                    </div>
                    {isSelected && (
                      <span
                        className="material-symbols-outlined text-primary flex-shrink-0 mt-0.5"
                        style={{ fontSize: '14px' }}
                      >
                        check
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>
    </>
  );
}

// ── Main Sidebar ───────────────────────────────────────────────────────────
export default function AgentSidebar() {
  const navigate = useNavigate();
  const {
    messages,
    isStreaming,
    provider,
    model,
    providerKeysStatus,
    keysStatusLoaded,
    sidebarOpen,
    setSidebarOpen,
    sendMessage,
    uploadFile,
    clearChat,
    fetchKeysStatus,
    generatedUiSpec,
  } = useAgentStore();

  const [input, setInput] = useState('');
  const [showProviderMenu, setShowProviderMenu] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Resizable Sidebar hooks
  const [width, setWidth] = useState(() => {
    const saved = localStorage.getItem('agent-sidebar-width');
    return saved ? parseInt(saved, 10) : 450;
  });
  const [isDragging, setIsDragging] = useState(false);

  const startResize = useCallback((mouseDownEvent: React.MouseEvent) => {
    mouseDownEvent.preventDefault();
    setIsDragging(true);
  }, []);

  const resize = useCallback((mouseMoveEvent: MouseEvent) => {
    const newWidth = window.innerWidth - mouseMoveEvent.clientX;
    if (newWidth >= 320 && newWidth <= 800) {
      setWidth(newWidth);
      localStorage.setItem('agent-sidebar-width', newWidth.toString());
    }
  }, []);

  const stopResize = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', resize);
      document.addEventListener('mouseup', stopResize);
    } else {
      document.removeEventListener('mousemove', resize);
      document.removeEventListener('mouseup', stopResize);
    }
    return () => {
      document.removeEventListener('mousemove', resize);
      document.removeEventListener('mouseup', stopResize);
    };
  }, [isDragging, resize, stopResize]);

  // Fetch key status on first open
  useEffect(() => {
    if (sidebarOpen && !keysStatusLoaded) {
      fetchKeysStatus();
    }
  }, [sidebarOpen, keysStatusLoaded, fetchKeysStatus]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Focus input on open
  useEffect(() => {
    if (sidebarOpen) {
      try { inputRef.current?.focus({ preventScroll: true }); } catch { inputRef.current?.focus(); }
    }
  }, [sidebarOpen]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput('');
    await sendMessage(text);
  }, [input, isStreaming, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      for (const file of acceptedFiles) {
        const path = await uploadFile(file);
        if (path) {
          await sendMessage(
            `I've uploaded "${file.name}". Please analyse this file and provide a summary of its contents.`
          );
        }
      }
    },
    [uploadFile, sendMessage]
  );

  const { getRootProps, getInputProps, isDragActive, open: openFilePicker } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    noClick: true,
    noKeyboard: true,
  });

  const currentProvider = PROVIDER_OPTIONS.find((p) => p.id === provider);
  const currentModel = currentProvider?.models.find((m) => m.id === model);
  const activeKey = providerKeysStatus[provider];

  // ── Collapsed tab ──────────────────────────────────────────────────────
  if (!sidebarOpen) {
    return (
      <button
        onClick={() => setSidebarOpen(true)}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-30 bg-gradient-to-b from-primary to-blue-600 text-white px-1.5 py-5 rounded-l-xl shadow-xl hover:opacity-90 transition-all group"
        title="Open AI Copilot"
      >
        <span
          className="material-symbols-outlined group-hover:scale-110 transition-transform"
          style={{ fontSize: '20px' }}
        >
          smart_toy
        </span>
      </button>
    );
  }

  // ── Suggestions ────────────────────────────────────────────────────────
  const suggestions = [
    'Build a custom UI layout to visualize my uploaded file',
    'What are the top 3 highest-risk LGAs?',
    'Correlate rainfall with cholera cases in Ogoja',
  ];

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 lg:hidden"
        onClick={() => setSidebarOpen(false)}
      />
      <aside
        className={`fixed inset-y-0 right-0 w-full max-w-md z-50 flex flex-col border-l border-[#e6e8eb] bg-white lg:static lg:z-20 lg:max-w-none lg:flex-shrink-0 relative ${
          isDragging ? 'select-none' : ''
        }`}
        style={{ width: typeof window !== 'undefined' && window.innerWidth >= 1024 ? `${width}px` : undefined }}
        {...getRootProps()}
      >
      {/* Resizer Handle */}
      <div
        className={`absolute top-0 left-0 bottom-0 w-1 cursor-col-resize z-50 transition-colors hover:bg-primary/45 ${
          isDragging ? 'bg-primary w-1.5' : ''
        }`}
        onMouseDown={startResize}
      />
      <input {...getInputProps()} />

      {/* Drag overlay */}
      {isDragActive && (
        <div className="absolute inset-0 z-50 bg-primary/10 border-2 border-dashed border-primary rounded-lg flex items-center justify-center backdrop-blur-sm">
          <div className="text-center">
            <span
              className="material-symbols-outlined text-primary mb-2"
              style={{ fontSize: '40px' }}
            >
              upload_file
            </span>
            <p className="text-primary font-semibold text-sm">Drop CSV / Excel file here</p>
          </div>
        </div>
      )}

      {/* ── Header (gradient glassmorphism) ─────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-[#0f172a] to-[#1e293b] flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="size-8 rounded-xl bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center shadow-lg shadow-primary/30">
            <span className="material-symbols-outlined text-white" style={{ fontSize: '18px' }}>
              smart_toy
            </span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-white leading-tight">AI Copilot</h3>
            <p className="text-[10px] text-slate-400 leading-tight">Surveillance Assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {/* Key status pill */}
          <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-semibold border ${
            activeKey
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : activeKey === false
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
              : 'bg-slate-500/10 border-slate-500/30 text-slate-400'
          }`}>
            <span className={`size-1.5 rounded-full ${
              activeKey ? 'bg-emerald-400 animate-pulse' : activeKey === false ? 'bg-amber-400' : 'bg-slate-500'
            }`} />
            {activeKey ? 'Live' : activeKey === false ? 'Mock' : '…'}
          </div>

          <button
            onClick={clearChat}
            className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 transition-colors"
            title="Clear chat"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
              delete_sweep
            </span>
          </button>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 transition-colors"
            title="Close sidebar"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
              close
            </span>
          </button>
        </div>
      </div>

      {/* ── Provider / Model Selector ──────────────────────────────────── */}
      <div className="px-3 py-2 border-b border-[#e6e8eb] bg-[#f8f9fb] flex-shrink-0 relative">
        <button
          id="agent-provider-trigger"
          onClick={() => setShowProviderMenu(!showProviderMenu)}
          className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-white border border-[#e6e8eb] hover:border-primary/40 hover:shadow-sm text-xs transition-all"
        >
          <span className="flex items-center gap-2 min-w-0">
            <span
              className="material-symbols-outlined text-[#637588]"
              style={{ fontSize: '14px' }}
            >
              {currentProvider?.icon || 'smart_toy'}
            </span>
            <span className="font-semibold text-[#111518] truncate">{currentProvider?.label}</span>
            <span className="text-[#94a3b8]">·</span>
            <span className="text-[#637588] font-mono text-[10px] truncate max-w-[130px]">
              {currentModel?.label || model}
            </span>
            {currentModel && (
              <TierBadge tier={currentModel.tier} />
            )}
          </span>
          <span
            className="material-symbols-outlined text-[#94a3b8] flex-shrink-0"
            style={{ fontSize: '16px' }}
          >
            {showProviderMenu ? 'expand_less' : 'expand_more'}
          </span>
        </button>

        <ProviderSelector
          open={showProviderMenu}
          onClose={() => setShowProviderMenu(false)}
        />
      </div>

      {/* ── Dashboard Notification Banner ── */}
      {generatedUiSpec && (
        <div className="mx-3 mt-3 p-3 bg-primary/5 border border-primary/20 rounded-xl flex items-center justify-between gap-3 animate-fade-in flex-shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className="material-symbols-outlined text-primary flex-shrink-0 animate-pulse" style={{ fontSize: '20px' }}>
              dashboard
            </span>
            <div className="min-w-0">
              <p className="text-[11px] font-bold text-[#1f2937] truncate">
                {generatedUiSpec.title || 'Dynamic Dashboard'}
              </p>
              <p className="text-[9px] text-[#6b7280] truncate">
                Interactive layout is ready to explore
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              navigate('/agent-explorer');
            }}
            className="flex-shrink-0 px-3 py-1.5 bg-primary hover:bg-primary/95 text-white font-semibold text-[10px] rounded-lg transition-all active:scale-95 shadow-md shadow-primary/10"
          >
            View UI
          </button>
        </div>
      )}

      {/* ── Chat Messages ──────────────────────────────────────────────── */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4"
      >
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4 py-8">
            {/* Icon */}
            <div className="size-16 rounded-2xl bg-gradient-to-br from-primary/10 to-blue-100 flex items-center justify-center mb-4 shadow-sm">
              <span
                className="material-symbols-outlined text-primary"
                style={{ fontSize: '32px' }}
              >
                psychology
              </span>
            </div>
            <h4 className="text-sm font-bold text-[#111518] mb-1">
              Cholera Surveillance Copilot
            </h4>
            <p className="text-xs text-[#637588] leading-relaxed mb-4 max-w-[260px]">
              Ask questions about LGA risk scores, case trends, and environmental data — or
              drop a CSV/Excel file and ask the Copilot to build a custom interactive UI layout for it!
            </p>

            {/* Key status summary */}
            <div className="w-full bg-[#f8f9fb] border border-[#e6e8eb] rounded-xl p-3 mb-4">
              <p className="text-[10px] font-semibold text-[#637588] uppercase tracking-wider mb-2">
                Provider Status
              </p>
              <div className="grid grid-cols-2 gap-1.5">
                {PROVIDER_OPTIONS.map((p) => (
                  <div key={p.id} className="flex items-center justify-between bg-white rounded-lg px-2.5 py-1.5 border border-[#e6e8eb]">
                    <span className="text-[10px] font-medium text-[#374151]">{p.label}</span>
                    <KeyBadge active={providerKeysStatus[p.id]} />
                  </div>
                ))}
              </div>
            </div>

            {/* Suggestions */}
            <div className="grid grid-cols-1 gap-2 w-full">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setInput(suggestion);
                    inputRef.current?.focus();
                  }}
                  className="text-left text-[11px] text-[#637588] bg-[#f8f9fb] hover:bg-primary/5 hover:text-primary px-3 py-2 rounded-xl border border-[#e6e8eb] transition-colors flex items-start gap-2"
                >
                  <span className="text-primary mt-0.5">→</span>
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              role={msg.role}
              content={msg.content}
              timestamp={msg.timestamp}
              isStreaming={msg.role === 'assistant' && msg.content === '' && isStreaming}
            />
          ))
        )}
      </div>

      {/* ── Input Area ─────────────────────────────────────────────────── */}
      <div className="border-t border-[#e6e8eb] px-3 py-3 bg-white flex-shrink-0">
        <div className="flex items-end gap-2">
          {/* Upload button */}
          <button
            id="agent-upload-btn"
            onClick={openFilePicker}
            disabled={isStreaming}
            className="flex items-center justify-center size-10 rounded-xl border border-[#e6e8eb] bg-[#f8f9fb] text-[#637588] hover:bg-primary/5 hover:text-primary hover:border-primary/30 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex-shrink-0 active:scale-95"
            title="Upload CSV or Excel file"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>add</span>
          </button>

          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              id="agent-chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about surveillance data…"
              rows={1}
              className="w-full resize-none rounded-xl border border-[#e6e8eb] bg-[#f8f9fb] px-3.5 py-2.5 text-sm text-[#111518] placeholder:text-[#94a3b8] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/40 transition-all"
              style={{ maxHeight: '120px', minHeight: '40px' }}
              disabled={isStreaming}
            />
          </div>
          <button
            id="agent-send-btn"
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="flex items-center justify-center size-10 rounded-xl bg-gradient-to-br from-primary to-blue-600 text-white hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md shadow-primary/25 hover:shadow-lg hover:shadow-primary/30 active:scale-95"
            title="Send message"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>
              {isStreaming ? 'hourglass_top' : 'send'}
            </span>
          </button>
        </div>
        <p className="text-[9px] text-[#94a3b8] mt-1.5 text-center">
          <span className="font-medium text-primary/60">+</span> to attach · Drop CSV/XLSX · Enter to send
        </p>
      </div>
      </aside>
    </>
  );
}
