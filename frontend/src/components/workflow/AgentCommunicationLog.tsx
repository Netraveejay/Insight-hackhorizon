import { useEffect, useRef } from 'react';
import { Radio, Zap, ArrowRight, AlertTriangle } from 'lucide-react';
import type { A2AMessage } from '../../api';
import { agentLabel } from './agentMeta';
import type { FlowKind } from './workflowUtils';

interface Props {
  messages: A2AMessage[];
  visibleCount: number;
}

const BADGE: Record<string, { label: string; className: string; Icon: typeof Radio }> = {
  handoff: { label: 'HANDOFF', className: 'bg-blue-500/20 text-blue-300 border-blue-500/40', Icon: ArrowRight },
  trigger: { label: 'TRIGGER', className: 'bg-amber-500/20 text-amber-300 border-amber-500/40', Icon: Zap },
  alert: { label: 'ALERT', className: 'bg-red-500/20 text-red-300 border-red-500/40', Icon: AlertTriangle },
  status: { label: 'STATUS', className: 'bg-slate-500/20 text-slate-300 border-slate-500/40', Icon: Radio },
  pipeline: { label: 'FLOW', className: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40', Icon: ArrowRight },
};

function formatLine(m: A2AMessage): { text: string; kind: FlowKind } {
  if (m.intent === 'alert') {
    return { text: `${agentLabel(m.from_agent)}: ${m.summary}`, kind: 'alert' };
  }
  if (m.intent === 'status' && m.to_agent === 'broadcast') {
    const prefix = m.status === 'processing'
      ? `${agentLabel(m.from_agent)} processing`
      : `${agentLabel(m.from_agent)} complete`;
    return { text: `${prefix}: ${m.summary}`, kind: 'status' };
  }
  const from = agentLabel(m.from_agent);
  const to = m.to_agent === 'broadcast' ? null : agentLabel(m.to_agent);
  const isTrigger = m.summary.toLowerCase().includes('p1') || m.summary.toLowerCase().includes('investigate');
  return {
    text: to ? `${from} → ${to}: ${m.summary}` : `${from}: ${m.summary}`,
    kind: isTrigger && m.intent === 'handoff' ? 'trigger' : 'handoff',
  };
}

export default function AgentCommunicationLog({
  messages,
  visibleCount,
}: Props) {
  const logRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const activeIndex = visibleCount > 0 ? visibleCount - 1 : -1;
  const shown = messages.slice(0, visibleCount);

  const handleScroll = () => {
    const el = logRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    stickToBottom.current = distanceFromBottom < 48;
  };

  useEffect(() => {
    const el = logRef.current;
    if (!el || !stickToBottom.current) return;
    el.scrollTop = el.scrollHeight;
  }, [activeIndex, shown.length]);

  return (
    <div className="flex flex-col h-full w-full overflow-hidden bg-slate-900">
      <div className="px-3 py-2 border-b border-slate-700 flex items-center justify-between bg-slate-800/80 shrink-0">
        <div className="flex items-center gap-1.5">
          <Radio size={12} className="text-emerald-400" />
          <span className="text-xs font-semibold text-slate-100">Communication</span>
        </div>
        <span className="text-[9px] text-slate-500 font-mono">
          {visibleCount}/{messages.length}
        </span>
      </div>

      <div
        ref={logRef}
        onScroll={handleScroll}
        className="flex-1 min-h-0 overflow-y-scroll scrollbar-panel px-1.5 py-1 space-y-0.5"
      >
        {messages.length === 0 && (
          <p className="text-slate-500 text-center py-8 text-[10px] font-sans px-2">
            Run pipeline to watch agent handoffs appear here.
          </p>
        )}
        {shown.map((m, i) => {
          const { text, kind } = formatLine(m);
          const badge = BADGE[kind] ?? BADGE.handoff;
          const isActive = i === activeIndex;
          const Icon = badge.Icon;

          return (
            <div
              key={m.id}
              className={`rounded px-2 py-1 border-l-2 transition-colors duration-300 ${
                isActive
                  ? 'bg-indigo-950/90 border-indigo-400'
                  : kind === 'alert' || kind === 'trigger'
                    ? 'bg-amber-950/20 border-amber-600/40 opacity-90'
                    : 'bg-slate-800/20 border-transparent opacity-75'
              }`}
            >
              <div className="flex items-center gap-1 mb-0.5">
                <span className="text-[8px] font-mono text-slate-600 w-3">{i + 1}</span>
                <span className={`inline-flex items-center gap-0.5 text-[7px] font-bold px-1 py-px rounded border ${badge.className}`}>
                  <Icon size={7} />
                  {badge.label}
                </span>
                <span className="text-[8px] text-slate-600 ml-auto font-mono">{formatTime(m.ts)}</span>
              </div>
              <p className={`text-[10px] leading-snug font-mono pl-4 ${isActive ? 'text-slate-100' : 'text-slate-500'}`}>
                {text}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function formatTime(ts: string): string {
  return new Date(ts).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });
}
