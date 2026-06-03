import { useRef, useEffect } from 'react';
import { useAgentStore } from '../../store/agentStore';

export default function SystemConsole() {
  const { thoughts, isStreaming, consoleOpen, setConsoleOpen, clearThoughts, consoleHeight } =
    useAgentStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new thoughts
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [thoughts]);

  return (
    <div
      className="panel-transition flex flex-col border-t border-[#1e293b] bg-[#0f172a] relative z-10 flex-shrink-0"
      style={{ height: consoleOpen ? `${consoleHeight}px` : '36px' }}
    >
      {/* Console Header Bar */}
      <div className="flex items-center justify-between h-9 px-3 bg-[#1e293b]/80 border-b border-[#334155] flex-shrink-0 select-none">
        <div className="flex items-center gap-2">
          {/* Traffic lights */}
          <div className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-[#ef4444]/80" />
            <span className="size-2.5 rounded-full bg-[#eab308]/80" />
            <span className="size-2.5 rounded-full bg-[#22c55e]/80" />
          </div>
          <span className="text-[11px] font-mono text-[#94a3b8] tracking-wide uppercase ml-2">
            System Console
          </span>
          {isStreaming && (
            <span className="flex items-center gap-1 ml-2">
              <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] text-emerald-400 font-mono">streaming</span>
            </span>
          )}
          {!isStreaming && thoughts.length > 0 && (
            <span className="text-[10px] text-[#64748b] font-mono ml-2">
              {thoughts.length} entries
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {thoughts.length > 0 && (
            <button
              onClick={clearThoughts}
              className="text-[10px] font-mono text-[#64748b] hover:text-[#94a3b8] px-1.5 py-0.5 rounded hover:bg-[#334155]/50 transition-colors"
              title="Clear console"
            >
              clear
            </button>
          )}
          <button
            onClick={() => setConsoleOpen(!consoleOpen)}
            className="p-0.5 rounded hover:bg-[#334155] text-[#94a3b8] hover:text-white transition-colors"
            title={consoleOpen ? 'Collapse console' : 'Expand console'}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
              {consoleOpen ? 'keyboard_arrow_down' : 'keyboard_arrow_up'}
            </span>
          </button>
        </div>
      </div>

      {/* Console Body */}
      {consoleOpen && (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto console-scrollbar p-3 font-mono text-[12px] leading-relaxed"
        >
          {thoughts.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-[#475569]">
              <span className="material-symbols-outlined mb-1" style={{ fontSize: '20px' }}>
                terminal
              </span>
              <span className="text-[11px]">Agent thoughts will appear here…</span>
            </div>
          ) : (
            <div className="space-y-1">
              {thoughts.map((t) => (
                <div key={t.id} className="flex gap-2">
                  <span className="text-[#6366f1] select-none flex-shrink-0">
                    {'>'}{' '}
                  </span>
                  <span className="text-[#e2e8f0] whitespace-pre-wrap break-words">
                    <span className="text-[#818cf8]">
                      [{new Date(t.timestamp).toLocaleTimeString('en-GB', { hour12: false })}]
                    </span>{' '}
                    {t.content}
                  </span>
                </div>
              ))}
              {isStreaming && (
                <span className="inline-block w-2 h-4 bg-emerald-400 animate-cursor ml-5" />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
