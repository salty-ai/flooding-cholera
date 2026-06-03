import { useState, useRef, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useAgentStore, PROVIDER_OPTIONS } from '../../store/agentStore';

export default function AgentSidebar() {
  const {
    messages,
    isStreaming,
    provider,
    model,
    sidebarOpen,
    setSidebarOpen,
    setProvider,
    setModel,
    sendMessage,
    uploadFile,
    clearChat,
  } = useAgentStore();

  const [input, setInput] = useState('');
  const [showProviderMenu, setShowProviderMenu] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Focus input on open
  useEffect(() => {
    if (sidebarOpen) inputRef.current?.focus();
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

  // File drop handling
  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      for (const file of acceptedFiles) {
        const path = await uploadFile(file);
        if (path) {
          await sendMessage(
            `I've uploaded "${file.name}". Please analyze this file and provide a summary of its contents.`
          );
        }
      }
    },
    [uploadFile, sendMessage]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
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

  if (!sidebarOpen) {
    return (
      <button
        onClick={() => setSidebarOpen(true)}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-30 bg-primary text-white px-1.5 py-4 rounded-l-lg shadow-lg hover:bg-primary/90 transition-colors group"
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

  return (
    <aside
      className="flex flex-col w-[380px] border-l border-[#e6e8eb] bg-white flex-shrink-0 z-20 panel-transition"
      {...getRootProps()}
    >
      <input {...getInputProps()} />

      {/* Drag overlay */}
      {isDragActive && (
        <div className="absolute inset-0 z-50 bg-primary/10 border-2 border-dashed border-primary rounded-lg flex items-center justify-center backdrop-blur-sm">
          <div className="text-center">
            <span className="material-symbols-outlined text-primary mb-2" style={{ fontSize: '40px' }}>
              upload_file
            </span>
            <p className="text-primary font-semibold text-sm">Drop CSV / Excel file here</p>
          </div>
        </div>
      )}

      {/* Sidebar Header */}
      <div className="flex items-center justify-between h-14 px-4 border-b border-[#e6e8eb] flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="size-8 rounded-lg bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center shadow-sm">
            <span className="material-symbols-outlined text-white" style={{ fontSize: '18px' }}>
              smart_toy
            </span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#111518] leading-tight">AI Copilot</h3>
            <p className="text-[10px] text-[#637588] leading-tight">Surveillance Assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={clearChat}
            className="p-1.5 rounded-lg hover:bg-[#f0f2f5] text-[#637588] transition-colors"
            title="Clear chat"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
              delete_sweep
            </span>
          </button>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-1.5 rounded-lg hover:bg-[#f0f2f5] text-[#637588] transition-colors"
            title="Close sidebar"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
              close
            </span>
          </button>
        </div>
      </div>

      {/* Provider / Model Selector */}
      <div className="px-4 py-2 border-b border-[#e6e8eb] bg-[#f8f9fb]">
        <div className="relative">
          <button
            onClick={() => setShowProviderMenu(!showProviderMenu)}
            className="w-full flex items-center justify-between gap-2 px-3 py-1.5 rounded-lg bg-white border border-[#e6e8eb] hover:border-primary/40 text-xs transition-colors"
          >
            <span className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-emerald-400" />
              <span className="font-medium text-[#111518]">{currentProvider?.label}</span>
              <span className="text-[#94a3b8]">·</span>
              <span className="text-[#637588] font-mono text-[11px] truncate max-w-[160px]">
                {model}
              </span>
            </span>
            <span className="material-symbols-outlined text-[#94a3b8]" style={{ fontSize: '16px' }}>
              {showProviderMenu ? 'expand_less' : 'expand_more'}
            </span>
          </button>

          {/* Dropdown */}
          {showProviderMenu && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-[#e6e8eb] rounded-lg shadow-lg z-30 max-h-60 overflow-y-auto custom-scrollbar">
              {PROVIDER_OPTIONS.map((p) => (
                <div key={p.id}>
                  <div className="px-3 py-1.5 text-[10px] font-semibold text-[#94a3b8] uppercase tracking-wider bg-[#f8f9fb]">
                    {p.label}
                  </div>
                  {p.models.map((m) => (
                    <button
                      key={m}
                      onClick={() => {
                        setProvider(p.id);
                        setModel(m);
                        setShowProviderMenu(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs hover:bg-primary/5 transition-colors flex items-center gap-2 ${
                        provider === p.id && model === m
                          ? 'text-primary font-medium bg-primary/5'
                          : 'text-[#374151]'
                      }`}
                    >
                      <span className="font-mono text-[11px]">{m}</span>
                      {provider === p.id && model === m && (
                        <span className="material-symbols-outlined text-primary ml-auto" style={{ fontSize: '14px' }}>
                          check
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chat Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-6">
            <div className="size-16 rounded-2xl bg-gradient-to-br from-primary/10 to-blue-100 flex items-center justify-center mb-4">
              <span className="material-symbols-outlined text-primary" style={{ fontSize: '32px' }}>
                psychology
              </span>
            </div>
            <h4 className="text-sm font-bold text-[#111518] mb-1">Cholera Surveillance Copilot</h4>
            <p className="text-xs text-[#637588] leading-relaxed mb-4">
              Ask questions about LGA risk scores, case trends, environmental data, or drop a CSV/Excel file for analysis.
            </p>
            <div className="grid grid-cols-1 gap-2 w-full">
              {[
                'What are the top 3 highest-risk LGAs?',
                'Correlate rainfall with cholera cases in Ogoja',
                'Show a summary of all case counts this month',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setInput(suggestion);
                    inputRef.current?.focus();
                  }}
                  className="text-left text-[11px] text-[#637588] bg-[#f8f9fb] hover:bg-primary/5 hover:text-primary px-3 py-2 rounded-lg border border-[#e6e8eb] transition-colors"
                >
                  <span className="text-primary mr-1">→</span>
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary text-white rounded-br-md'
                    : 'bg-[#f0f2f5] text-[#111518] rounded-bl-md'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="flex items-center gap-1 mb-1">
                    <span className="material-symbols-outlined text-primary" style={{ fontSize: '12px' }}>
                      smart_toy
                    </span>
                    <span className="text-[10px] font-semibold text-[#637588]">Copilot</span>
                  </div>
                )}
                <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                {msg.role === 'assistant' && msg.content === '' && isStreaming && (
                  <div className="flex items-center gap-1 py-1">
                    <span className="size-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="size-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="size-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                )}
                <span className="block text-[9px] mt-1 opacity-50">
                  {new Date(msg.timestamp).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-[#e6e8eb] px-4 py-3 bg-white flex-shrink-0">
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about surveillance data..."
              rows={1}
              className="w-full resize-none rounded-xl border border-[#e6e8eb] bg-[#f8f9fb] px-3.5 py-2.5 text-sm text-[#111518] placeholder:text-[#94a3b8] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/40 transition-all"
              style={{ maxHeight: '120px', minHeight: '40px' }}
              disabled={isStreaming}
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="flex items-center justify-center size-10 rounded-xl bg-primary text-white hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow-md active:scale-95"
            title="Send message"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>
              {isStreaming ? 'hourglass_top' : 'send'}
            </span>
          </button>
        </div>
        <p className="text-[9px] text-[#94a3b8] mt-1.5 text-center">
          Drop CSV/XLSX files into chat · Enter to send · Shift+Enter for new line
        </p>
      </div>
    </aside>
  );
}
