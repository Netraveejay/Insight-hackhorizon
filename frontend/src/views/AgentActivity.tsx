import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Brain, Loader2, Play, Zap } from 'lucide-react';
import { api, AgentRunDetail, AgentRunSummary, ReasoningStep } from '../api';

const TRIGGER_ICON: Record<string, string> = {
  schedule: '🕐',
  detection: '⚡',
  anomaly: '📈',
  question: '💬',
  manual: '👆',
};

const PHASE_STYLE: Record<string, string> = {
  think: 'border-l-indigo-400 bg-indigo-50',
  act: 'border-l-blue-500 bg-blue-50',
  observe: 'border-l-emerald-500 bg-emerald-50',
  reflect: 'border-l-amber-500 bg-amber-50',
  final: 'border-l-purple-500 bg-purple-50',
};

interface Props {
  week: string;
}

export default function AgentActivity({ week }: Props) {
  const [params, setParams] = useSearchParams();
  const [runs, setRuns] = useState<AgentRunSummary[]>([]);
  const [active, setActive] = useState<AgentRunDetail | null>(null);
  const [liveSteps, setLiveSteps] = useState<ReasoningStep[]>([]);
  const [running, setRunning] = useState(false);
  const timelineRef = useRef<HTMLDivElement>(null);

  const loadRuns = useCallback(() => {
    api.agentRuns(40).then((r) => setRuns(r.runs)).catch(() => null);
  }, []);

  const loadRun = useCallback(async (id: string) => {
    const run = await api.agentRun(id);
    setActive(run);
    setLiveSteps(run.steps);
    setParams({ run: id });
  }, [setParams]);

  useEffect(() => {
    loadRuns();
    const runId = params.get('run');
    if (runId) loadRun(runId);
  }, [loadRuns, params, loadRun]);

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = import.meta.env.VITE_API_URL
      ? new URL(import.meta.env.VITE_API_URL).host
      : window.location.host;
    const path = import.meta.env.VITE_API_URL ? '/runs/stream' : '/api/runs/stream';
    const ws = new WebSocket(`${proto}://${host}${path}`);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === 'ping') return;
        if (data.type === 'step') {
          const step = data.step as ReasoningStep;
          if (!active || data.run_id === active.id) {
            setLiveSteps((prev) => {
              const exists = prev.some((s) => s.step_no === step.step_no && s.phase === step.phase);
              if (exists) return prev;
              return [...prev, step].sort((a, b) => a.step_no - b.step_no);
            });
          }
          loadRuns();
        }
        if (data.type === 'run_complete' && data.run?.id === active?.id) {
          loadRun(data.run.id);
        }
      } catch {
        /* ignore */
      }
    };
    return () => ws.close();
  }, [active?.id, loadRun, loadRuns]);

  useEffect(() => {
    if (timelineRef.current) timelineRef.current.scrollTop = timelineRef.current.scrollHeight;
  }, [liveSteps]);

  const runPipeline = async () => {
    setRunning(true);
    try {
      await api.agenticPipelineRun(week);
      loadRuns();
    } finally {
      setRunning(false);
    }
  };

  const display = active ? { ...active, steps: liveSteps.length ? liveSteps : active.steps } : null;

  return (
    <div className="space-y-4 max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold text-accent uppercase tracking-wider flex items-center gap-1">
            <Brain size={14} /> Agent activity
          </p>
          <h2 className="text-2xl font-bold text-slate-900 mt-1">Triggers & reasoning workflow</h2>
          <p className="text-sm text-slate-600 mt-1">
            Every agentic run shows what triggered it and each think → act → observe step, streamed live.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={runPipeline}
            disabled={running}
            className="flex items-center gap-2 bg-accent text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60"
          >
            {running ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            Run pipeline
          </button>
          <Link to="/agents" className="border px-4 py-2 rounded-lg text-sm bg-white hover:bg-slate-50">
            Agent graph
          </Link>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <div className="space-y-2 lg:col-span-1 max-h-[600px] overflow-y-auto">
          <p className="text-xs font-semibold text-slate-500 uppercase">Recent runs</p>
          {runs.length === 0 && (
            <p className="text-sm text-slate-400 p-4 border rounded-xl bg-white">No agent runs yet.</p>
          )}
          {runs.map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => loadRun(r.id)}
              className={`w-full text-left p-3 rounded-xl border transition-colors ${
                active?.id === r.id ? 'border-accent bg-blue-50' : 'bg-white hover:border-slate-300'
              }`}
            >
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span>{TRIGGER_ICON[r.trigger?.type || 'manual']}</span>
                <span className="capitalize">{r.trigger?.type || r.runner}</span>
                <span className={`ml-auto px-1.5 py-0.5 rounded text-[10px] ${
                  r.status === 'done' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'
                }`}>
                  {r.status}
                </span>
              </div>
              <p className="text-sm font-medium text-slate-800 mt-1 line-clamp-2">
                {r.trigger?.summary || r.goal}
              </p>
              <p className="text-[10px] text-slate-400 mt-1">{r.runner} · {r.started_at?.slice(0, 19)}</p>
            </button>
          ))}
        </div>

        <div className="lg:col-span-2 space-y-4">
          {!display && (
            <div className="bg-white border rounded-2xl p-12 text-center text-slate-500">
              <Zap className="mx-auto mb-3 text-slate-300" size={32} />
              <p>Select a run, investigate an issue, or ask the Assistant to see the reasoning trace.</p>
            </div>
          )}

          {display && (
            <>
              <div className="bg-gradient-to-r from-slate-800 to-slate-700 text-white rounded-2xl p-5">
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{TRIGGER_ICON[display.trigger?.type || 'manual']}</span>
                  <div>
                    <p className="text-xs text-slate-300 uppercase tracking-wider">Trigger</p>
                    <p className="font-semibold text-lg mt-0.5">
                      {display.trigger?.summary || 'Agent run'}
                    </p>
                    <p className="text-sm text-slate-300 mt-1">
                      {display.trigger?.type} · {display.trigger?.source} ·{' '}
                      {display.trigger?.ts?.slice(0, 19) || display.started_at?.slice(0, 19)}
                    </p>
                    <p className="text-sm mt-3 text-slate-200">
                      <span className="text-slate-400">Goal:</span> {display.goal}
                    </p>
                    <p className="text-xs text-slate-400 mt-2">Runner: {display.runner}</p>
                  </div>
                </div>
              </div>

              <div ref={timelineRef} className="bg-white border rounded-2xl p-4 max-h-[480px] overflow-y-auto space-y-3">
                <p className="text-xs font-semibold text-slate-500 uppercase sticky top-0 bg-white py-1">
                  Reasoning workflow ({display.steps.length} steps)
                </p>
                {display.steps.map((step) => (
                  <StepCard key={`${step.step_no}-${step.phase}`} step={step} />
                ))}
                {display.outcome && (
                  <div className="border-l-4 border-purple-500 bg-purple-50 rounded-r-xl p-4 mt-4">
                    <p className="text-xs font-semibold text-purple-800 uppercase">Final outcome</p>
                    <p className="text-sm text-slate-800 mt-2 whitespace-pre-wrap">{display.outcome}</p>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function StepCard({ step }: { step: ReasoningStep }) {
  return (
    <div className={`border-l-4 rounded-r-xl p-3 ${PHASE_STYLE[step.phase] || 'bg-slate-50'}`}>
      <div className="flex items-center gap-2 text-[10px] text-slate-500 mb-1">
        <span className="font-bold text-slate-700">#{step.step_no + 1}</span>
        <span className="uppercase font-semibold">{step.phase}</span>
        <span>·</span>
        <span>{step.agent}</span>
      </div>
      <p className="text-sm text-slate-800">
        <span className="text-slate-500">💭 Thought:</span> {step.thought}
      </p>
      {step.action && (
        <p className="text-sm text-slate-700 mt-1 font-mono text-xs bg-white/60 rounded px-2 py-1 mt-2">
          🛠 Action: {step.action.tool}({JSON.stringify(step.action.input).slice(0, 100)})
        </p>
      )}
      {step.observation && (
        <p className="text-sm text-slate-600 mt-1">
          <span className="text-slate-500">👁 Observation:</span> {step.observation}
        </p>
      )}
    </div>
  );
}
