import type { LucideIcon } from 'lucide-react';
import {
  Bell, Brain, CheckCircle2, Circle, Clock, Database, Filter,
  GitBranch, Languages, Loader2, Radar, Scale, Search, Send, Sparkles,
  AlertCircle,
} from 'lucide-react';
import type { AgentCardMeta } from './agentMeta';

export interface AgentVisual {
  Icon: LucideIcon;
  gradient: string;
  accent: string;
  ring: string;
  tagline: string;
}

export const AGENT_VISUALS: Record<string, AgentVisual> = {
  connector: {
    Icon: Database,
    gradient: 'from-blue-600 to-cyan-700',
    accent: 'text-cyan-300',
    ring: 'ring-cyan-500/40',
    tagline: 'Collects guest feedback',
  },
  ingestion: {
    Icon: Filter,
    gradient: 'from-emerald-600 to-teal-700',
    accent: 'text-emerald-300',
    ring: 'ring-emerald-500/40',
    tagline: 'Clean & normalise',
  },
  translation: {
    Icon: Languages,
    gradient: 'from-sky-600 to-blue-700',
    accent: 'text-sky-300',
    ring: 'ring-sky-500/40',
    tagline: 'Multilingual bridge',
  },
  scoring: {
    Icon: Scale,
    gradient: 'from-indigo-600 to-violet-700',
    accent: 'text-indigo-300',
    ring: 'ring-indigo-500/40',
    tagline: 'Themes & sentiment',
  },
  clustering: {
    Icon: GitBranch,
    gradient: 'from-violet-600 to-purple-700',
    accent: 'text-violet-300',
    ring: 'ring-violet-500/40',
    tagline: 'Site × theme groups',
  },
  detection: {
    Icon: Radar,
    gradient: 'from-orange-600 to-amber-700',
    accent: 'text-orange-300',
    ring: 'ring-orange-500/40',
    tagline: 'Spikes & priorities',
  },
  root_cause: {
    Icon: Search,
    gradient: 'from-amber-600 to-yellow-700',
    accent: 'text-amber-300',
    ring: 'ring-amber-500/40',
    tagline: 'Why is this happening?',
  },
  sla: {
    Icon: Clock,
    gradient: 'from-rose-600 to-pink-700',
    accent: 'text-rose-300',
    ring: 'ring-rose-500/40',
    tagline: 'Response clocks',
  },
  insight: {
    Icon: Brain,
    gradient: 'from-purple-600 to-fuchsia-700',
    accent: 'text-purple-300',
    ring: 'ring-purple-500/40',
    tagline: 'Drafts recommendations',
  },
  output: {
    Icon: Send,
    gradient: 'from-slate-600 to-slate-800',
    accent: 'text-slate-300',
    ring: 'ring-slate-500/40',
    tagline: 'Alerts & reports',
  },
  explainability: {
    Icon: Sparkles,
    gradient: 'from-teal-600 to-emerald-800',
    accent: 'text-teal-300',
    ring: 'ring-teal-500/40',
    tagline: 'Plain-language narrative',
  },
  orchestrator: {
    Icon: Bell,
    gradient: 'from-indigo-600 to-blue-800',
    accent: 'text-indigo-300',
    ring: 'ring-indigo-500/40',
    tagline: 'Sequences the run',
  },
};

interface Props {
  id: string;
  meta: AgentCardMeta;
  status: 'idle' | 'processing' | 'done' | 'error';
  metric?: string;
  durationMs?: number;
  totalItems?: number;
  highlighted: boolean;
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'processing') {
    return (
      <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-amber-300 bg-amber-500/20 px-1.5 py-0.5 rounded-full">
        <Loader2 size={10} className="animate-spin" /> Running
      </span>
    );
  }
  if (status === 'done') {
    return (
      <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-emerald-300 bg-emerald-500/20 px-1.5 py-0.5 rounded-full">
        <CheckCircle2 size={10} /> Done
      </span>
    );
  }
  if (status === 'error') {
    return (
      <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-red-300 bg-red-500/20 px-1.5 py-0.5 rounded-full">
        <AlertCircle size={10} /> Error
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[9px] text-slate-500 bg-slate-700/50 px-1.5 py-0.5 rounded-full">
      <Circle size={8} /> Idle
    </span>
  );
}

export default function AgentNodeCard({
  id, meta, status, metric, durationMs, totalItems, highlighted,
}: Props) {
  const visual = AGENT_VISUALS[id] ?? AGENT_VISUALS.ingestion;
  const Icon = visual.Icon;
  const isLlm = meta.type === 'llm';
  const displayMetric = id === 'connector' && totalItems != null
    ? `${totalItems} items ingested`
    : metric || (status === 'idle' ? 'Awaiting trigger…' : '');

  return (
    <div
      className={`h-full flex flex-col rounded-2xl overflow-hidden bg-slate-900/95 border transition-all duration-500 ${
        highlighted
          ? `border-indigo-400 shadow-xl shadow-indigo-500/30 ring-2 ${visual.ring} scale-[1.03]`
          : status === 'processing'
            ? 'border-amber-500/70 shadow-lg shadow-amber-500/20'
            : status === 'done'
              ? 'border-emerald-600/50'
              : 'border-slate-700/80'
      }`}
    >
      {/* Header with gradient + avatar */}
      <div className={`relative px-3 pt-3 pb-2 bg-gradient-to-br ${visual.gradient}`}>
        {meta.order != null && (
          <span className="absolute top-2 left-2 w-5 h-5 rounded-md bg-black/30 text-[10px] font-bold text-white flex items-center justify-center">
            {meta.order}
          </span>
        )}
        {isLlm && (
          <span className="absolute top-2 right-2 text-[8px] font-bold bg-purple-900/80 text-purple-200 px-1.5 py-0.5 rounded border border-purple-400/40">
            LLM
          </span>
        )}
        <div className="flex flex-col items-center pt-1">
          <div className={`w-12 h-12 rounded-2xl bg-black/25 backdrop-blur flex items-center justify-center mb-1.5 ${
            highlighted ? 'animate-pulse' : ''
          }`}>
            <Icon size={26} className="text-white drop-shadow" strokeWidth={1.75} />
          </div>
          <p className="text-[11px] font-bold text-white text-center leading-tight tracking-tight px-1">
            {meta.displayName}
          </p>
          <p className={`text-[9px] ${visual.accent} mt-0.5 text-center`}>{visual.tagline}</p>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 px-3 py-2 flex flex-col min-h-0">
        <div className="flex justify-center mb-2">
          <StatusBadge status={status} />
        </div>
        <ul className="space-y-0.5 flex-1">
          {meta.tasks.slice(0, 2).map((t) => (
            <li key={t} className="text-[9px] text-slate-400 flex items-center gap-1.5">
              <span className="w-1 h-1 rounded-full bg-slate-500 shrink-0" />
              {t}
            </li>
          ))}
        </ul>
        <div className="mt-auto pt-2 border-t border-slate-700/60">
          <p className="text-[9px] text-emerald-400/90 leading-snug line-clamp-2">{displayMetric}</p>
          {durationMs != null && (
            <p className="text-[8px] text-slate-500 font-mono mt-0.5">{durationMs} ms</p>
          )}
        </div>
      </div>
    </div>
  );
}
