import { CheckCircle2, Circle } from 'lucide-react';
import { FLOW_PHASES } from './workflowUtils';

interface Props {
  activePhaseId: string | null;
  completedPhaseIds: Set<string>;
}

export default function FlowPhaseRail({ activePhaseId, completedPhaseIds }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-3 space-y-1">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 px-1 mb-2">
        Process phases
      </p>
      {FLOW_PHASES.map((phase) => {
        const active = activePhaseId === phase.id;
        const done = completedPhaseIds.has(phase.id);
        return (
          <div
            key={phase.id}
            className={`flex gap-2.5 px-2 py-2 rounded-lg transition-all duration-500 ${
              active
                ? 'bg-indigo-950/80 border border-indigo-500/50 shadow-md shadow-indigo-900/30'
                : done
                  ? 'bg-slate-800/40 border border-transparent'
                  : 'border border-transparent opacity-50'
            }`}
          >
            <div className="mt-0.5 shrink-0">
              {done ? (
                <CheckCircle2 size={14} className="text-emerald-400" />
              ) : active ? (
                <span className="relative flex h-3.5 w-3.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-60" />
                  <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-indigo-500" />
                </span>
              ) : (
                <Circle size={14} className="text-slate-600" />
              )}
            </div>
            <div className="min-w-0">
              <p className={`text-xs font-semibold ${active ? 'text-indigo-200' : 'text-slate-300'}`}>
                {phase.short}. {phase.label}
              </p>
              <p className="text-[10px] text-slate-500 leading-snug mt-0.5">{phase.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
