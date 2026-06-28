import { AlertTriangle, ArrowRight, GitBranch, Loader2, Radio, Zap } from 'lucide-react';
import { FLOW_PHASES, type FlowStep } from './workflowUtils';

interface Props {
  step: FlowStep | null;
  nextStep: FlowStep | null;
  stepIndex: number;
  totalSteps: number;
  isPlaying: boolean;
}

const KIND_STYLE: Record<string, { bg: string; border: string; icon: typeof Radio }> = {
  pipeline: { bg: 'bg-blue-950/80', border: 'border-blue-500/60', icon: ArrowRight },
  trigger: { bg: 'bg-amber-950/80', border: 'border-amber-500/70', icon: Zap },
  alert: { bg: 'bg-red-950/80', border: 'border-red-500/70', icon: AlertTriangle },
  status: { bg: 'bg-slate-800/90', border: 'border-slate-500/50', icon: Loader2 },
  agentic: { bg: 'bg-purple-950/80', border: 'border-purple-500/60', icon: GitBranch },
  handoff: { bg: 'bg-indigo-950/80', border: 'border-indigo-500/60', icon: ArrowRight },
};

export default function CurrentStepBanner({
  step,
  nextStep,
  stepIndex,
  totalSteps,
  isPlaying,
}: Props) {
  const phase = step ? FLOW_PHASES.find((p) => p.id === step.phaseId) : null;
  const style = step ? KIND_STYLE[step.kind] ?? KIND_STYLE.handoff : null;
  const Icon = style?.icon ?? Radio;

  return (
    <div className="bg-slate-900/95 border border-slate-700 rounded-xl px-4 py-3 shadow-lg">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {isPlaying && (
            <span className="relative flex h-3 w-3 shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
            </span>
          )}
          <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
              {step ? (
                <>Step {stepIndex + 1} of {totalSteps} · Phase {phase?.short}: {phase?.label}</>
              ) : isPlaying ? (
                'Starting workflow…'
              ) : (
                'Run pipeline to watch agents work together'
              )}
            </p>
            {step && (
              <p className="text-sm font-semibold text-white truncate mt-0.5">{step.title}</p>
            )}
            {step && (
              <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{step.subtitle}</p>
            )}
            {!step && nextStep && isPlaying && (
              <p className="text-xs text-slate-400 mt-0.5">
                Up next: <span className="text-slate-300">{nextStep.title}</span>
              </p>
            )}
          </div>
        </div>

        {step && style && (
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border shrink-0 ${style.bg} ${style.border}`}>
            <Icon size={16} className={step.kind === 'trigger' || step.kind === 'alert' ? 'text-amber-400' : 'text-blue-400'} />
            <div className="text-[10px]">
              <p className="font-bold text-slate-200 uppercase tracking-wide">
                {step.kind === 'trigger' ? 'Trigger fired' : step.kind === 'pipeline' ? 'Data flow' : step.kind}
              </p>
              {step.edgeKey && (
                <p className="text-slate-400 font-mono">{step.edgeKey.replace('->', ' → ')}</p>
              )}
            </div>
          </div>
        )}
      </div>

      {totalSteps > 0 && (
        <div className="mt-3 flex gap-0.5">
          {Array.from({ length: Math.min(totalSteps, 50) }).map((_, i) => {
            const filled = i <= stepIndex;
            const current = i === stepIndex;
            return (
              <div
                key={i}
                className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                  current ? 'bg-indigo-400' : filled ? 'bg-indigo-600/60' : 'bg-slate-700'
                }`}
                title={`Step ${i + 1}`}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
