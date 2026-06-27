import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Play, Loader2, Zap, Database, Languages, Tags, Layers,
  AlertTriangle, Lightbulb, Send, BookOpen, ChevronRight, Info,
} from 'lucide-react';
import { api, PipelineExplanation, PipelineRunResult, StepExplanation } from '../api';
import Tag from '../components/Tag';

const FLOW_STEPS = [
  { id: 'trigger', label: 'Trigger', icon: Zap },
  { id: 'ingest', label: 'Ingest', icon: Database },
  { id: 'translate', label: 'Translate', icon: Languages },
  { id: 'score', label: 'Score', icon: Tags },
  { id: 'cluster', label: 'Cluster', icon: Layers },
  { id: 'detect', label: 'Detect', icon: AlertTriangle },
  { id: 'insight', label: 'Insight', icon: Lightbulb },
  { id: 'output', label: 'Output', icon: Send },
  { id: 'explain', label: 'Explain', icon: BookOpen },
] as const;

interface Props {
  week: string;
}

export default function Pipeline({ week }: Props) {
  const [running, setRunning] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const [result, setResult] = useState<PipelineRunResult | null>(null);
  const [explanation, setExplanation] = useState<PipelineExplanation | null>(null);
  const [expandedStep, setExpandedStep] = useState<string | null>('ingest');
  const [error, setError] = useState('');
  const [connectors, setConnectors] = useState<import('../api').ConnectorsStatus | null>(null);

  useEffect(() => {
    api.connectors().then(setConnectors).catch(() => null);
  }, []);

  useEffect(() => {
    api.pipelineExplain(week)
      .then((r) => {
        setExplanation(r.explanation);
        setExpandedStep('ingest');
      })
      .catch(() => setExplanation(null));
  }, [week]);

  const run = async () => {
    setRunning(true);
    setError('');
    setResult(null);
    setActiveIdx(0);
    try {
      const res = await api.runPipeline(week);
      for (let i = 0; i < FLOW_STEPS.length; i++) {
        setActiveIdx(i);
        await new Promise((r) => setTimeout(r, 350));
      }
      setResult(res);
      if (res.explanation) setExplanation(res.explanation);
      setActiveIdx(FLOW_STEPS.length);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Pipeline failed');
      setActiveIdx(-1);
    } finally {
      setRunning(false);
    }
  };

  const explainSteps = explanation?.steps ?? [];

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold text-accent uppercase tracking-wider">Agent pipeline</p>
          <h2 className="text-2xl font-bold text-slate-900 mt-1">How feedback becomes action</h2>
          <p className="text-sm text-slate-600 mt-2 max-w-xl">
            Eight specialised agents process guest and staff messages for week <strong>{week}</strong>.
            The Explainability Agent narrates each step in plain language.
          </p>
        </div>
        <button
          onClick={run}
          disabled={running}
          className="flex items-center justify-center gap-2 bg-accent text-white px-6 py-3 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-60 shadow-sm transition-all shrink-0"
        >
          {running ? <Loader2 size={20} className="animate-spin" /> : <Play size={20} />}
          {running ? 'Running…' : 'Run full pipeline'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-xl p-4 text-sm">{error}</div>
      )}

      {/* Narrative headline */}
      {explanation && (
        <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-2xl p-6 shadow-lg">
          <p className="text-blue-300 text-xs font-semibold uppercase tracking-wider mb-2">Explainability Agent</p>
          <h3 className="text-xl font-bold leading-snug">{explanation.headline}</h3>
          <p className="text-slate-300 text-sm mt-3 leading-relaxed">{explanation.summary}</p>
          <p className="text-slate-500 text-xs mt-4 flex items-center gap-1.5">
            <Info size={12} />
            {explanation.audience_note}
          </p>
        </div>
      )}

      {/* Visual flow */}
      <div className="bg-white border rounded-2xl p-5 overflow-x-auto">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">End-to-end flow</p>
        <div className="flex items-center gap-1 min-w-max">
          {FLOW_STEPS.map((step, i) => {
            const done = result ? true : activeIdx > i;
            const active = running && activeIdx === i;
            const Icon = step.icon;
            return (
              <div key={step.id} className="flex items-center">
                <button
                  type="button"
                  onClick={() => step.id !== 'trigger' && step.id !== 'explain' && setExpandedStep(step.id)}
                  className={`flex flex-col items-center w-20 py-2 rounded-xl transition-all ${
                    active ? 'bg-blue-100 ring-2 ring-accent' : done ? 'bg-green-50' : 'bg-slate-50'
                  } ${step.id !== 'trigger' && step.id !== 'explain' ? 'cursor-pointer hover:bg-blue-50' : ''}`}
                >
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center mb-1 ${
                    active ? 'bg-accent text-white' : done ? 'bg-green-600 text-white' : 'bg-slate-200 text-slate-600'
                  }`}>
                    {active ? <Loader2 size={16} className="animate-spin" /> : <Icon size={16} />}
                  </div>
                  <span className="text-[10px] font-medium text-slate-700 text-center leading-tight">{step.label}</span>
                </button>
                {i < FLOW_STEPS.length - 1 && (
                  <ChevronRight size={16} className="text-slate-300 mx-0.5 shrink-0" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* Step detail */}
        <div className="lg:col-span-3 space-y-3">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">What each agent did</p>
          {!explanation && !running && (
            <div className="bg-slate-100 border border-dashed border-slate-300 rounded-xl p-8 text-center text-slate-500 text-sm">
              Run the pipeline to see a plain-language walkthrough of every agent step.
            </div>
          )}
          {explainSteps.map((step) => (
            <StepCard
              key={step.id}
              step={step}
              expanded={expandedStep === step.id}
              onToggle={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
              count={result?.steps.find((s) => s.id === step.id)?.count}
            />
          ))}
        </div>

        {/* Sidebar: hero + outputs + glossary */}
        <div className="lg:col-span-2 space-y-4">
          {explanation?.hero && (
            <div className="bg-blue-50 border border-accent/30 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Tag priority={explanation.hero.priority} />
                <span className="text-xs font-bold text-accent uppercase">Top priority</span>
              </div>
              <h4 className="font-bold text-slate-900">{explanation.hero.headline}</h4>
              <p className="text-sm text-slate-700 mt-2 leading-relaxed">{explanation.hero.story}</p>
              <ul className="mt-3 space-y-1.5">
                {explanation.hero.reasons.map((r) => (
                  <li key={r} className="text-xs text-slate-600 flex gap-2">
                    <span className="text-accent shrink-0">•</span>
                    {r}
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-accent/20">
                <Link to="/issues" className="text-xs font-medium text-accent hover:underline">Issues →</Link>
                <Link to="/feed" className="text-xs font-medium text-slate-600 hover:underline">Live Feed →</Link>
                <Link to="/alerts" className="text-xs font-medium text-slate-600 hover:underline">Alerts →</Link>
              </div>
            </div>
          )}

          {result && (
            <div className="bg-white border rounded-2xl p-5">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Where it went</p>
              <div className="space-y-2">
                {result.outputs.map((o) => (
                  <div key={o.type} className="flex justify-between items-center text-sm py-1.5 border-b border-slate-100 last:border-0">
                    <span className="text-slate-700">{o.label}</span>
                    <span className="font-bold text-accent tabular-nums">{o.count}</span>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-slate-400 mt-3">Run {result.run_id} · rules v{result.rules_version}</p>
            </div>
          )}

          {explanation && Object.keys(explanation.glossary).length > 0 && (
            <div className="bg-white border rounded-2xl p-5">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Key terms</p>
              <dl className="space-y-3">
                {Object.entries(explanation.glossary).map(([term, def]) => (
                  <div key={term}>
                    <dt className="text-xs font-semibold text-slate-800">{term}</dt>
                    <dd className="text-xs text-slate-500 mt-0.5 leading-relaxed">{def}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>
      </div>

      {connectors && connectors.mode === 'seed' && (
        <div className="bg-white border rounded-2xl p-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Going live without mock data</p>
          <p className="text-sm text-slate-700">
            Today the pipeline reads <strong>synthetic seed data</strong> for demos. To use real feedback:
          </p>
          <ol className="text-sm text-slate-600 mt-3 space-y-2 list-decimal list-inside">
            <li>Export guest/staff feedback as JSON (same schema as seed file)</li>
            <li>Set <code className="bg-slate-100 px-1 rounded text-xs">FEEDBACK_FILE_PATH=data/inbound/feedback.json</code> in <code className="bg-slate-100 px-1 rounded text-xs">backend/.env</code></li>
            <li>Set <code className="bg-slate-100 px-1 rounded text-xs">TEAMS_WEBHOOK_URL</code> for real Teams alerts</li>
            <li>Re-run the pipeline — connectors switch from seed to your file automatically</li>
          </ol>
          <p className="text-xs text-slate-500 mt-3">
            M365 inbox, Google reviews, and social connectors are stubbed for a future phase.
          </p>
        </div>
      )}
    </div>
  );
}

const STEP_ICONS: Record<string, typeof Database> = {
  ingest: Database,
  translate: Languages,
  score: Tags,
  cluster: Layers,
  detect: AlertTriangle,
  insight: Lightbulb,
  output: Send,
};

function StepCard({
  step,
  expanded,
  onToggle,
  count,
}: {
  step: StepExplanation;
  expanded: boolean;
  onToggle: () => void;
  count?: number;
}) {
  const Icon = STEP_ICONS[step.id] ?? BookOpen;
  return (
    <div className={`border rounded-xl overflow-hidden transition-shadow ${expanded ? 'shadow-md border-accent/40' : 'bg-white'}`}>
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-3 p-4 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
          <Icon size={18} className="text-slate-700" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm text-slate-900">{step.label}</p>
          <p className="text-xs text-slate-500 truncate">{step.input_label} → {step.output_label}</p>
        </div>
        {count !== undefined && count > 0 && (
          <span className="text-lg font-bold text-accent tabular-nums shrink-0">{count}</span>
        )}
        <ChevronRight size={16} className={`text-slate-400 shrink-0 transition-transform ${expanded ? 'rotate-90' : ''}`} />
      </button>
      {expanded && (
        <div className="px-4 pb-4 pt-0 border-t border-slate-100 bg-slate-50/50">
          <div className="grid sm:grid-cols-2 gap-4 mt-3">
            <div>
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">What happened</p>
              <p className="text-sm text-slate-700 leading-relaxed">{step.what_happened}</p>
            </div>
            <div>
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Why it matters</p>
              <p className="text-sm text-slate-700 leading-relaxed">{step.why_it_matters}</p>
            </div>
          </div>
          {step.highlights.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-2">
              {step.highlights.map((h) => (
                <li key={h} className="text-[11px] bg-white border border-slate-200 rounded-full px-2.5 py-1 text-slate-600">
                  {h}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
