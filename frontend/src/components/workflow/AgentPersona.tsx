import type { LucideIcon } from 'lucide-react';
import {
  Brain, CheckCircle2, Circle, Clock, Database, Filter, GitBranch, Languages,
  Loader2, Radar, Scale, Search, Send, Sparkles, AlertCircle,
} from 'lucide-react';
import type { AgentCardMeta } from './agentMeta';

export interface AgentVisual {
  Icon: LucideIcon;
  bodyGradient: string;
  glowColor: string;
  platformColor: string;
  description: string;
}

export const AGENT_VISUALS: Record<string, AgentVisual> = {
  connector: {
    Icon: Database,
    bodyGradient: 'from-cyan-400 to-blue-600',
    glowColor: 'shadow-cyan-500/50',
    platformColor: 'from-cyan-500/70 to-blue-600/30',
    description: 'Google Reviews · QR · Email · Surveys',
  },
  ingestion: {
    Icon: Filter,
    bodyGradient: 'from-emerald-400 to-teal-600',
    glowColor: 'shadow-emerald-500/50',
    platformColor: 'from-emerald-500/70 to-teal-600/30',
    description: 'Normalize · dedupe · spam · PII',
  },
  translation: {
    Icon: Languages,
    bodyGradient: 'from-sky-400 to-blue-600',
    glowColor: 'shadow-sky-500/50',
    platformColor: 'from-sky-500/70 to-blue-600/30',
    description: 'Detect language · translate · retain originals',
  },
  scoring: {
    Icon: Scale,
    bodyGradient: 'from-indigo-400 to-violet-600',
    glowColor: 'shadow-indigo-500/50',
    platformColor: 'from-indigo-500/70 to-violet-600/30',
    description: 'Sentiment · themes · urgency · relevance',
  },
  clustering: {
    Icon: GitBranch,
    bodyGradient: 'from-violet-400 to-purple-600',
    glowColor: 'shadow-violet-500/50',
    platformColor: 'from-violet-500/70 to-purple-600/30',
    description: 'Group by site · theme · week',
  },
  detection: {
    Icon: Radar,
    bodyGradient: 'from-orange-400 to-amber-600',
    glowColor: 'shadow-orange-500/50',
    platformColor: 'from-orange-500/70 to-amber-600/30',
    description: 'Spikes · compounding · cross-source',
  },
  root_cause: {
    Icon: Search,
    bodyGradient: 'from-amber-400 to-yellow-600',
    glowColor: 'shadow-amber-500/50',
    platformColor: 'from-amber-500/70 to-yellow-600/30',
    description: 'Keywords & taxonomy → root cause',
  },
  sla: {
    Icon: Clock,
    bodyGradient: 'from-rose-400 to-pink-600',
    glowColor: 'shadow-rose-500/50',
    platformColor: 'from-rose-500/70 to-pink-600/30',
    description: 'Response clocks · breach warnings',
  },
  insight: {
    Icon: Brain,
    bodyGradient: 'from-purple-400 to-fuchsia-600',
    glowColor: 'shadow-purple-500/50',
    platformColor: 'from-purple-500/70 to-fuchsia-600/30',
    description: 'Recommendations & action points',
  },
  output: {
    Icon: Send,
    bodyGradient: 'from-slate-300 to-slate-600',
    glowColor: 'shadow-slate-400/40',
    platformColor: 'from-slate-400/60 to-slate-600/30',
    description: 'Teams alerts · digest · site reports',
  },
  explainability: {
    Icon: Sparkles,
    bodyGradient: 'from-teal-400 to-emerald-600',
    glowColor: 'shadow-teal-500/50',
    platformColor: 'from-teal-500/70 to-emerald-600/30',
    description: 'Plain-language decision narrative',
  },
};

interface Props {
  id: string;
  meta: AgentCardMeta;
  status: 'idle' | 'processing' | 'done' | 'error';
  metric?: string;
  highlighted: boolean;
  totalItems?: number;
}

function statusLabel(status: string): { text: string; className: string } {
  switch (status) {
    case 'processing': return { text: 'Processing…', className: 'text-amber-300' };
    case 'done': return { text: 'Complete ✓', className: 'text-emerald-300' };
    case 'error': return { text: 'Error', className: 'text-red-300' };
    default: return { text: 'Standing by', className: 'text-slate-500' };
  }
}

export default function AgentPersona({ id, meta, status, metric, highlighted, totalItems }: Props) {
  const visual = AGENT_VISUALS[id] ?? AGENT_VISUALS.ingestion;
  const Icon = visual.Icon;
  const st = statusLabel(status);
  const isActive = highlighted || status === 'processing';
  const isLlm = meta.type === 'llm';

  const footnote = id === 'connector' && totalItems != null
    ? `${totalItems} items`
    : metric?.length
      ? (metric.length > 36 ? `${metric.slice(0, 34)}…` : metric)
      : null;

  const displayName = meta.displayName.replace(/Agent$/, '').trim() || meta.displayName;

  return (
    <div
      className={`flex flex-col items-center select-none transition-transform duration-500 w-full ${
        isActive ? 'scale-105 z-20' : 'scale-100 z-10'
      }`}
    >
      <div className="relative mb-2">
        {isActive && (
          <div className={`absolute -inset-4 rounded-full blur-2xl opacity-50 bg-gradient-to-b ${visual.bodyGradient}`} />
        )}
        <div
          className={`relative w-[88px] h-[88px] rounded-full bg-gradient-to-br ${visual.bodyGradient}
            flex items-center justify-center border-[3px] border-white/30 shadow-2xl ${visual.glowColor}
            ${isActive ? 'ring-4 ring-white/35' : ''}`}
        >
          <Icon size={42} className="text-white drop-shadow-md" strokeWidth={1.4} />
          {meta.order != null && (
            <span className="absolute -top-1 -left-1 w-6 h-6 rounded-full bg-slate-900 border-2 border-white/50 text-[10px] font-bold text-white flex items-center justify-center">
              {meta.order}
            </span>
          )}
          {isLlm && (
            <span className="absolute -top-1.5 -right-1.5 text-[9px] font-bold bg-purple-900 text-purple-200 px-2 py-0.5 rounded-full border border-purple-400/50">
              LLM
            </span>
          )}
          {status === 'processing' && (
            <span className="absolute -bottom-1.5 -right-1.5 bg-amber-500 rounded-full p-1 shadow-lg">
              <Loader2 size={16} className="text-white animate-spin" />
            </span>
          )}
          {status === 'done' && (
            <span className="absolute -bottom-1.5 -right-1.5 bg-emerald-500 rounded-full p-1 shadow-lg">
              <CheckCircle2 size={16} className="text-white" />
            </span>
          )}
          {status === 'error' && (
            <span className="absolute -bottom-1.5 -right-1.5 bg-red-500 rounded-full p-1 shadow-lg">
              <AlertCircle size={16} className="text-white" />
            </span>
          )}
        </div>

        <div
          className={`absolute left-1/2 -translate-x-1/2 top-[82px] w-[96px] h-[12px] rounded-[100%] bg-gradient-to-b ${visual.platformColor} blur-[2px]`}
        />
        <div
          className={`absolute left-1/2 -translate-x-1/2 top-[84px] w-[76px] h-[8px] rounded-[100%] bg-gradient-to-b ${visual.platformColor}`}
        />
      </div>

      <p className="text-xs font-bold text-white text-center leading-tight mt-3 px-1">
        {displayName}
      </p>
      <p className="text-[10px] text-slate-400 text-center leading-snug mt-1 px-1 h-[26px]">
        {visual.description}
      </p>
      <p className={`text-[11px] font-medium mt-2 ${st.className}`}>
        {status === 'idle' ? (
          <span className="inline-flex items-center gap-1"><Circle size={9} /> {st.text}</span>
        ) : st.text}
      </p>
      {footnote && (
        <p className="text-[10px] text-cyan-300/90 mt-1.5 text-center font-mono max-w-full truncate px-2">
          {footnote}
        </p>
      )}
    </div>
  );
}
