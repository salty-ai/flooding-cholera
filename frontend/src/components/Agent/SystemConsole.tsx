import { useRef, useEffect, useCallback } from 'react';
import { useAgentStore } from '../../store/agentStore';

type ThoughtKind = 'tool_exec' | 'tool_output' | 'info' | 'warn' | 'success' | 'default';

function classifyThought(content: string): ThoughtKind {
  if (content.startsWith('🔧')) return 'tool_exec';
  if (content.startsWith('📦')) return 'tool_output';
  if (content.startsWith('❌') || content.startsWith('⚠️')) return 'warn';
  if (content.startsWith('💬') || content.startsWith('✅')) return 'success';
  if (content.startsWith('Mock') || content.startsWith('Checking')) return 'info';
  return 'default';
}

const KIND_STYLES: Record<ThoughtKind, { prefix: string; prefixClass: string; textClass: string }> = {
  tool_exec:  { prefix: '❯ TOOL', prefixClass: 'text-violet-400', textClass: 'text-violet-200' },
  tool_output:{ prefix: '❯ OUT ', prefixClass: 'text-emerald-400', textClass: 'text-emerald-200' },
  warn:       { prefix: '❯ WARN', prefixClass: 'text-amber-400', textClass: 'text-amber-200' },
  success:    { prefix: '❯ SYS ', prefixClass: 'text-sky-400', textClass: 'text-sky-200' },
  info:       { prefix: '❯ INFO', prefixClass: 'text-slate-400', textClass: 'text-slate-300' },
  default:    { prefix: '❯     ', prefixClass: 'text-[#6366f1]', textClass: 'text-[#e2e8f0]' },
};

function ThoughtLine({ content, timestamp }: { content: string; timestamp: number }) {
  const kind = classifyThought(content);
  const { prefix, prefixClass, textClass } = KIND_STYLES[kind];
  const timeStr = new Date(timestamp).toLocaleTimeString('en-GB', { hour12: false });

  return (
    <div className="flex gap-2 items-start py-0.5 hover:bg-white/5 rounded px-1 transition-colors group">
      <span className={`font-mono text-[10px] flex-shrink-0 select-none font-bold ${prefixClass}`}>
        {prefix}
      </span>
      <span className={`font-mono text-[11px] ${textClass} whitespace-pre-wrap break-words flex-1 leading-relaxed`}>
        <span className="text-[#475569] mr-2 group-hover:text-[#64748b] transition-colors">
          [{timeStr}]
        </span>
        {content}
      </span>
    </div>
  );
}

export default function SystemConsole() {
  const {
    thoughts,
    isStreaming,
    consoleOpen,
    setConsoleOpen,
    clearThoughts,
    consoleHeight,
  } = useAgentStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new thoughts
  useEffect(() => {
    if (scrollRef.current && consoleOpen) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [thoughts, consoleOpen]);

  const handleToggle = useCallback(
    () => setConsoleOpen(!consoleOpen),
    [consoleOpen, setConsoleOpen]
  );

  return (
    <div
      className="panel-transition flex flex-col border-t border-[#1e293b] bg-[#0a0f1e] relative z-10 flex-shrink-0"
      style={{ height: consoleOpen ? `${consoleHeight}px` : '36px' }}
    >
      {/* ── Console Header Bar ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between h-9 px-3 bg-[#0f172a] border-b border-[#1e293b] flex-shrink-0 select-none">
        <div className="flex items-center gap-3">
          {/* macOS traffic lights */}
          <div className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-[#ef4444]/80 hover:bg-[#ef4444] transition-colors cursor-pointer" title="Close" />
            <span className="size-2.5 rounded-full bg-[#eab308]/80 hover:bg-[#eab308] transition-colors cursor-pointer" title="Minimize" />
            <span className="size-2.5 rounded-full bg-[#22c55e]/80 hover:bg-[#22c55e] transition-colors cursor-pointer" title="Expand" />
          </div>

          <span className="text-[10px] font-mono text-[#64748b] tracking-widest uppercase ml-1">
            System Console
          </span>

          {/* Live indicator */}
          {isStreaming && (
            <span className="flex items-center gap-1.5 ml-1">
              <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[9px] text-emerald-400 font-mono uppercase tracking-wider">
                streaming
              </span>
            </span>
          )}

          {/* Entry count */}
          {!isStreaming && thoughts.length > 0 && (
            <span className="text-[9px] text-[#475569] font-mono ml-1">
              {thoughts.length} entries
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {thoughts.length > 0 && (
            <button
              id="console-clear-btn"
              onClick={clearThoughts}
              className="text-[9px] font-mono text-[#475569] hover:text-[#94a3b8] px-2 py-0.5 rounded hover:bg-[#1e293b] transition-colors uppercase tracking-wider"
              title="Clear console"
            >
              clear
            </button>
          )}
          <button
            id="console-toggle-btn"
            onClick={handleToggle}
            className="p-0.5 rounded hover:bg-[#1e293b] text-[#64748b] hover:text-[#94a3b8] transition-colors"
            title={consoleOpen ? 'Collapse console' : 'Expand console'}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
              {consoleOpen ? 'keyboard_arrow_down' : 'keyboard_arrow_up'}
            </span>
          </button>
        </div>
      </div>

      {/* ── Console Body ────────────────────────────────────────────────── */}
      {consoleOpen && (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto console-scrollbar px-2 py-2"
        >
          {thoughts.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-[#334155]">
              <span className="material-symbols-outlined mb-1.5 text-[#1e293b]" style={{ fontSize: '22px' }}>
                terminal
              </span>
              <span className="text-[10px] font-mono">Agent thoughts will appear here…</span>
            </div>
          ) : (
            <div>
              {thoughts.map((t) => (
                <ThoughtLine key={t.id} content={t.content} timestamp={t.timestamp} />
              ))}
              {isStreaming && (
                <div className="flex items-center gap-2 px-1 py-0.5">
                  <span className="text-[#6366f1] font-mono text-[10px] font-bold select-none">❯    </span>
                  <span className="inline-block w-2 h-3.5 bg-emerald-400 animate-cursor" />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
