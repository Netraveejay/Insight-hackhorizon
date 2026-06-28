import { Link } from 'react-router-dom';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Loader2, Play, RotateCcw, Network, Activity, SkipForward, Gauge,
} from 'lucide-react';
import { api, A2AMessage } from '../api';
import WorkflowCanvas, { buildEdgeLabels, buildNodeMetrics } from '../components/workflow/WorkflowCanvas';
import AgentCommunicationLog from '../components/workflow/AgentCommunicationLog';
import CurrentStepBanner from '../components/workflow/CurrentStepBanner';
import FlowPhaseRail from '../components/workflow/FlowPhaseRail';
import { PIPELINE_AGENT_IDS } from '../components/workflow/agentMeta';
import {
  buildFlowSteps,
  replayStatusAt,
  SPEED_PRESETS,
  type FlowStep,
} from '../components/workflow/workflowUtils';

type NodeStatus = 'idle' | 'processing' | 'done' | 'error';

interface Props {
  week: string;
}

export default function AgentNetwork({ week }: Props) {
  const [allMessages, setAllMessages] = useState<A2AMessage[]>([]);
  const [visibleCount, setVisibleCount] = useState(0);
  const [nodeStatus, setNodeStatus] = useState<Record<string, NodeStatus>>({});
  const [activeEdge, setActiveEdge] = useState<string | null>(null);
  const [activeEdgeKind, setActiveEdgeKind] = useState<'pipeline' | 'trigger' | 'agentic' | null>(null);
  const [completedEdges, setCompletedEdges] = useState<Set<string>>(new Set());
  const [highlightedNode, setHighlightedNode] = useState<string | null>(null);
  const [correlationId, setCorrelationId] = useState<string>('live');
  const [correlations, setCorrelations] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speedId, setSpeedId] = useState<string>('normal');
  const [execStatus, setExecStatus] = useState<'idle' | 'running' | 'completed'>('idle');
  const [totalItems, setTotalItems] = useState<number | undefined>();
  const replayAbort = useRef(false);
  const wsRef = useRef<WebSocket | null>(null);
  const workflowRef = useRef<HTMLDivElement>(null);
  const [panelHeight, setPanelHeight] = useState(0);
  const speedMsRef = useRef<number>(1400);

  const speedMs = SPEED_PRESETS.find((s) => s.id === speedId)?.ms ?? 1400;
  speedMsRef.current = speedMs;

  const flowSteps = useMemo(() => buildFlowSteps(allMessages), [allMessages]);
  const currentStep: FlowStep | null = visibleCount > 0 ? flowSteps[visibleCount - 1] ?? null : null;
  const nextStep: FlowStep | null = visibleCount < flowSteps.length ? flowSteps[visibleCount] ?? null : null;
  const visibleMessages = allMessages.slice(0, visibleCount);

  const activePhaseId = currentStep?.phaseId ?? (visibleCount < allMessages.length ? nextStep?.phaseId ?? null : null);
  const completedPhaseIds = useMemo(() => {
    const done = new Set<string>();
    const phases = ['start', 'ingest', 'analyze', 'trigger', 'output'];
    const currentIdx = phases.indexOf(activePhaseId ?? '');
    for (let i = 0; i < currentIdx; i++) done.add(phases[i]);
    if (execStatus === 'completed') return new Set(phases);
    return done;
  }, [activePhaseId, execStatus]);

  const applyStep = useCallback((step: FlowStep, upToIndex: number, messages: A2AMessage[]) => {
    setNodeStatus(replayStatusAt(messages, upToIndex));
    setHighlightedNode(step.toAgent ?? step.fromAgent);
    if (step.edgeKey) {
      setActiveEdge(step.edgeKey);
      setActiveEdgeKind(step.edgeKind);
      setCompletedEdges((prev) => new Set([...prev, step.edgeKey!]));
      if (step.kind === 'trigger' || step.kind === 'alert') {
        setTimeout(() => setActiveEdge(null), 2500);
      }
    } else {
      setActiveEdge(null);
      setActiveEdgeKind(null);
    }
    const m = step.message;
    if (m.from_agent === 'connector' && m.intent === 'status' && m.status === 'done') {
      const match = m.summary.match(/(\d+)/);
      if (match) setTotalItems(parseInt(match[1], 10));
    }
  }, []);

  const resetVisuals = useCallback(() => {
    setVisibleCount(0);
    setNodeStatus({});
    setActiveEdge(null);
    setActiveEdgeKind(null);
    setCompletedEdges(new Set());
    setHighlightedNode(null);
    setExecStatus('idle');
  }, []);

  const playAuto = useCallback(async (messages: A2AMessage[]) => {
    replayAbort.current = false;
    setIsPlaying(true);
    setExecStatus('running');
    resetVisuals();
    setAllMessages(messages);
    const steps = buildFlowSteps(messages);

    for (let i = 0; i < steps.length; i++) {
      if (replayAbort.current) break;
      setVisibleCount(i + 1);
      applyStep(steps[i], i, messages);
      const base = speedMsRef.current;
      const delay = steps[i].kind === 'trigger' || steps[i].kind === 'alert' ? base * 1.5 : base;
      await new Promise((r) => setTimeout(r, delay));
    }

    if (!replayAbort.current) {
      setExecStatus('completed');
      setActiveEdge(null);
      setHighlightedNode(null);
    }
    setIsPlaying(false);
  }, [applyStep, resetVisuals]);

  useEffect(() => {
    api.a2aCorrelations().then((r) => setCorrelations(r.correlation_ids)).catch(() => null);
  }, []);

  useEffect(() => {
    const el = workflowRef.current;
    if (!el) return;

    const update = () => {
      const h = el.getBoundingClientRect().height;
      if (h > 0) setPanelHeight(h);
    };

    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;
    replayAbort.current = true;
    setIsPlaying(false);
    resetVisuals();
    setAllMessages([]);

    api.pipelineWorkflow(week).then(async (w) => {
      if (cancelled || w.messages.length === 0) return;
      setCorrelationId(w.correlation_id);
      await playAuto(w.messages);
    }).catch(() => null);

    return () => {
      cancelled = true;
      replayAbort.current = true;
    };
  }, [week, resetVisuals, playAuto]);

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = import.meta.env.VITE_API_URL
      ? new URL(import.meta.env.VITE_API_URL).host
      : window.location.host;
    const path = import.meta.env.VITE_API_URL ? '/a2a/ws' : '/api/a2a/ws';
    const ws = new WebSocket(`${proto}://${host}${path}`);
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === 'ping') return;
        if (correlationId !== 'live' && data.correlation_id !== correlationId) return;
        if (isPlaying) return;
        setAllMessages((prev) => {
          if (prev.some((p) => p.id === data.id)) return prev;
          return [...prev.slice(-199), data as A2AMessage];
        });
      } catch {
        /* ignore */
      }
    };
    return () => ws.close();
  }, [correlationId, isPlaying]);

  const nodeMetrics = useMemo(() => buildNodeMetrics(visibleMessages), [visibleMessages]);
  const edgeLabels = useMemo(() => buildEdgeLabels(visibleMessages), [visibleMessages]);

  const progress = useMemo(() => {
    if (allMessages.length === 0) return 0;
    return Math.round((visibleCount / allMessages.length) * 100);
  }, [visibleCount, allMessages.length]);

  const loadHistory = async (cid: string) => {
    replayAbort.current = true;
    setIsPlaying(false);
    setCorrelationId(cid);
    if (cid === 'live') {
      resetVisuals();
      setAllMessages([]);
      return;
    }
    const res = await api.a2aMessages(cid);
    await playAuto(res.messages);
  };

  const runPipeline = async () => {
    replayAbort.current = true;
    setRunning(true);
    resetVisuals();
    setAllMessages([]);
    setCorrelationId('live');
    setTotalItems(undefined);
    try {
      const res = await api.a2aRun(week);
      const cid = res.a2a_correlation_id || res.run_id;
      setCorrelationId(cid);
      setTotalItems(res.items_ingested);
      api.a2aCorrelations().then((r) => setCorrelations(r.correlation_ids)).catch(() => null);
      const hist = await api.a2aMessages(cid);
      await playAuto(hist.messages);
    } finally {
      setRunning(false);
    }
  };

  const replay = () => {
    if (allMessages.length === 0) return;
    playAuto(allMessages);
  };

  const skipToEnd = () => {
    replayAbort.current = true;
    setIsPlaying(false);
    setVisibleCount(allMessages.length);
    setNodeStatus(replayStatusAt(allMessages, allMessages.length - 1));
    setExecStatus('completed');
    setActiveEdge(null);
    setHighlightedNode(null);
    const edges = new Set<string>();
    buildFlowSteps(allMessages).forEach((s) => {
      if (s.edgeKey) edges.add(s.edgeKey);
    });
    setCompletedEdges(edges);
  };

  return (
    <div className="space-y-4 max-w-[1680px]">
      <div className="bg-slate-900 text-white rounded-xl border border-slate-700 px-5 py-4 shadow-lg">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
              <Network size={14} /> Agent Network
            </p>
            <h2 className="text-xl font-bold mt-1">Workflow Execution</h2>
            <p className="text-sm text-slate-400 mt-0.5">
              Week {week} · agents run automatically after you start the pipeline
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={runPipeline}
              disabled={running || isPlaying}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60"
            >
              {running ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
              Run pipeline
            </button>
            <button
              onClick={replay}
              disabled={isPlaying || allMessages.length === 0}
              className="flex items-center gap-2 border border-slate-600 bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-lg text-sm text-slate-200 disabled:opacity-50"
            >
              <RotateCcw size={16} /> Replay
            </button>
            <button
              onClick={skipToEnd}
              disabled={allMessages.length === 0 || isPlaying}
              className="flex items-center gap-2 border border-slate-600 bg-slate-800 px-3 py-2 rounded-lg text-sm text-slate-200 disabled:opacity-40"
            >
              <SkipForward size={16} /> Skip all
            </button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="flex justify-between text-[10px] text-slate-500 mb-1">
              <span>Flow progress</span>
              <span>{progress}% · {visibleCount}/{allMessages.length} steps</span>
            </div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-600 via-purple-500 to-amber-500 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Gauge size={14} className="text-slate-500" />
            <span className="text-xs text-slate-500">Speed</span>
            {SPEED_PRESETS.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => setSpeedId(s.id)}
                className={`text-xs px-2.5 py-1 rounded-full border ${
                  speedId === s.id ? 'bg-indigo-600 border-indigo-500 text-white' : 'border-slate-600 text-slate-400'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <CurrentStepBanner
        step={currentStep}
        nextStep={nextStep}
        stepIndex={visibleCount > 0 ? visibleCount - 1 : 0}
        totalSteps={allMessages.length}
        isPlaying={isPlaying}
      />

      <div className="flex flex-wrap gap-3 items-center text-sm">
        <label className="text-slate-500 text-xs">Past run</label>
        <select
          value={correlationId}
          onChange={(e) => loadHistory(e.target.value)}
          className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 bg-white"
        >
          <option value="live">Live stream</option>
          {correlations.map((c) => (
            <option key={c} value={c}>#{c.slice(0, 12)}</option>
          ))}
        </select>
        <div className="flex flex-wrap gap-4 text-xs text-slate-500 ml-auto">
          <span className="flex items-center gap-1.5">
            <span className="w-6 h-0.5 bg-blue-500 rounded" /> Data flow
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-6 border-t-2 border-dashed border-amber-500" /> Trigger branch
          </span>
        </div>
      </div>

      <div className="flex flex-col xl:flex-row gap-3 items-start">
        <FlowPhaseRail activePhaseId={activePhaseId} completedPhaseIds={completedPhaseIds} />

        <div className="flex flex-1 min-w-0 gap-3">
          <div
            ref={workflowRef}
            className="flex-1 min-w-0 rounded-2xl overflow-hidden border border-slate-700/80 shadow-2xl"
          >
            <WorkflowCanvas
              nodeStatus={nodeStatus}
              nodeMetrics={nodeMetrics}
              activeEdge={activeEdge}
              activeEdgeKind={activeEdgeKind}
              highlightedNode={highlightedNode}
              completedEdges={completedEdges}
              edgeLabels={edgeLabels}
              totalItems={totalItems}
            />
          </div>

          <div
            className="w-[220px] shrink-0 rounded-2xl overflow-hidden border border-slate-700 shadow-2xl flex flex-col"
            style={panelHeight > 0 ? { height: panelHeight } : undefined}
          >
            <AgentCommunicationLog
              messages={allMessages}
              visibleCount={visibleCount}
            />
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500 px-1">
        <span className="flex items-center gap-1.5">
          <Activity size={12} className="text-emerald-500" />
          {PIPELINE_AGENT_IDS.filter((id) => nodeStatus[id] === 'done').length}/{PIPELINE_AGENT_IDS.length} agents done
          {isPlaying && (
            <span className="text-indigo-400">· workflow running…</span>
          )}
        </span>
        <Link to="/activity" className="text-accent hover:underline">Agent Activity → reasoning traces</Link>
      </div>
    </div>
  );
}
