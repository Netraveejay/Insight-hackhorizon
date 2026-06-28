import {
  AGENT_META,
  CARD_H,
  CARD_W,
  PIPELINE_AGENT_IDS,
  WORKFLOW_EDGES,
  WORKFLOW_LAYOUT,
  agentLabel,
  type EdgeKind,
} from './agentMeta';
import AgentNodeCard from './AgentNodeCard';
import type { A2AMessage } from '../../api';

export interface NodeMetrics {
  summary?: string;
  count?: string;
  durationMs?: number;
}

interface Props {
  nodeStatus: Record<string, 'idle' | 'processing' | 'done' | 'error'>;
  nodeMetrics: Record<string, NodeMetrics>;
  activeEdge: string | null;
  activeEdgeKind: EdgeKind | null;
  highlightedNode: string | null;
  completedEdges: Set<string>;
  totalItems?: number;
}

function edgePath(x1: number, y1: number, x2: number, y2: number): string {
  const dx = x2 - x1;
  const cx = x1 + dx * 0.42;
  return `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`;
}

function edgeEndpoints(from: string, to: string) {
  const a = WORKFLOW_LAYOUT[from];
  const b = WORKFLOW_LAYOUT[to];
  if (!a || !b) return null;
  const x1 = a.x + CARD_W;
  const y1 = a.y + CARD_H / 2;
  const x2 = b.x;
  const y2 = b.y + CARD_H / 2;
  return { x1, y1, x2, y2, path: edgePath(x1, y1, x2, y2) };
}

function edgeStyle(kind: EdgeKind, active: boolean, completed: boolean) {
  if (active) return { stroke: '#60a5fa', width: 4, dash: undefined, opacity: 1 };
  if (completed) {
    switch (kind) {
      case 'trigger': return { stroke: '#f59e0b', width: 2.5, dash: '10 6', opacity: 0.6 };
      default: return { stroke: '#475569', width: 2.5, dash: undefined, opacity: 0.55 };
    }
  }
  switch (kind) {
    case 'trigger': return { stroke: '#92400e', dash: '10 6', width: 2, opacity: 0.35 };
    default: return { stroke: '#1e293b', width: 2, dash: undefined, opacity: 0.5 };
  }
}

const VIEW_W = 1980;
const VIEW_H = 620;

export default function WorkflowGraph({
  nodeStatus,
  nodeMetrics,
  activeEdge,
  activeEdgeKind,
  highlightedNode,
  completedEdges,
  totalItems,
}: Props) {
  const visibleIds = new Set([...PIPELINE_AGENT_IDS, 'orchestrator']);
  const activeEp = activeEdge ? (() => {
    const [from, to] = activeEdge.split('->');
    return edgeEndpoints(from, to);
  })() : null;

  return (
    <div className="relative bg-[#0a0f1a] min-h-[580px] overflow-auto">
      <style>{`
        @keyframes flow-dash { to { stroke-dashoffset: -36; } }
        @keyframes flow-pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
        .edge-flow-active { stroke-dasharray: 12 8; animation: flow-dash 1.4s linear infinite; }
      `}</style>

      {/* Subtle grid */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: 'radial-gradient(circle, #64748b 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }}
      />

      <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="relative w-full min-w-[1100px] h-[580px]">
        <defs>
          <marker id="wf-arrow-pipeline" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" fill="#3b82f6" opacity="0.7" />
          </marker>
          <marker id="wf-arrow-trigger" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" fill="#f59e0b" />
          </marker>
          <marker id="wf-arrow-active" markerWidth="12" markerHeight="12" refX="9" refY="5" orient="auto">
            <path d="M0,0 L9,5 L0,10 Z" fill="#60a5fa" />
          </marker>
          <filter id="glow-strong">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* Zone backgrounds — soft, not boxy */}
        <ellipse cx="620" cy="280" rx="580" ry="130" fill="#1e3a5f" opacity="0.12" />
        <ellipse cx="1480" cy="130" rx="200" ry="90" fill="#78350f" opacity="0.1" />
        <ellipse cx="1480" cy="470" rx="320" ry="100" fill="#4c1d95" opacity="0.1" />

        <text x="48" y="148" className="fill-slate-500 text-[11px] font-semibold tracking-[0.2em]">
          DATA PIPELINE
        </text>
        <text x="1380" y="48" className="fill-amber-600/80 text-[10px] font-semibold tracking-[0.15em]">
          TRIGGERED
        </text>
        <text x="1280" y="378" className="fill-purple-500/70 text-[10px] font-semibold tracking-[0.15em]">
          INSIGHT &amp; OUTPUT
        </text>

        {WORKFLOW_EDGES.filter(({ from }) => visibleIds.has(from) || WORKFLOW_LAYOUT[from]).map(({ from, to, kind }) => {
          const ep = edgeEndpoints(from, to);
          if (!ep) return null;
          const key = `${from}->${to}`;
          const active = activeEdge === key;
          const completed = completedEdges.has(key);
          const style = edgeStyle(kind, active, completed);
          const marker = active ? 'url(#wf-arrow-active)' : kind === 'trigger' ? 'url(#wf-arrow-trigger)' : 'url(#wf-arrow-pipeline)';

          return (
            <g key={key}>
              <path
                d={ep.path}
                fill="none"
                stroke={style.stroke}
                strokeWidth={style.width}
                strokeDasharray={style.dash}
                markerEnd={marker}
                opacity={style.opacity}
                className={active ? 'edge-flow-active' : ''}
                strokeLinecap="round"
              />
              {active && activeEdgeKind === 'trigger' && (
                <text
                  x={(ep.x1 + ep.x2) / 2}
                  y={(ep.y1 + ep.y2) / 2 - 12}
                  textAnchor="middle"
                  className="fill-amber-300 text-[11px] font-bold"
                  style={{ animation: 'flow-pulse 1.5s ease-in-out infinite' }}
                >
                  ⚡ TRIGGER
                </text>
              )}
            </g>
          );
        })}

        {activeEp && (
          <>
            <circle r="8" fill="#60a5fa" opacity="0.35" filter="url(#glow-strong)">
              <animateMotion dur="2s" repeatCount="indefinite" path={activeEp.path} />
            </circle>
            <circle r="4" fill="#93c5fd">
              <animateMotion dur="2s" repeatCount="indefinite" path={activeEp.path} />
            </circle>
          </>
        )}

        {Array.from(visibleIds).map((id) => {
          const pos = WORKFLOW_LAYOUT[id];
          const meta = AGENT_META[id];
          if (!pos || !meta) return null;
          const st = nodeStatus[id] || 'idle';
          const metrics = nodeMetrics[id];
          const isHighlighted = highlightedNode === id;

          return (
            <foreignObject
              key={id}
              x={pos.x}
              y={pos.y}
              width={CARD_W}
              height={CARD_H}
              className="overflow-visible"
            >
              <AgentNodeCard
                id={id}
                meta={meta}
                status={st}
                metric={metrics?.summary}
                durationMs={metrics?.durationMs}
                totalItems={id === 'connector' ? totalItems : undefined}
                highlighted={isHighlighted}
              />
            </foreignObject>
          );
        })}
      </svg>
    </div>
  );
}

export function buildNodeMetrics(messages: A2AMessage[]): Record<string, NodeMetrics> {
  const metrics: Record<string, NodeMetrics> = {};
  const started: Record<string, number> = {};

  for (const m of messages) {
    const ts = new Date(m.ts).getTime();
    if (m.intent === 'handoff' && m.to_agent !== 'broadcast') {
      started[m.to_agent] = ts;
    }
    if (m.intent === 'status' && m.status === 'processing' && m.from_agent !== 'broadcast') {
      started[m.from_agent] = started[m.from_agent] ?? ts;
    }
    if (m.intent === 'status' && m.status === 'done' && m.from_agent !== 'broadcast') {
      const agent = m.from_agent;
      const dur = started[agent] ? ts - started[agent] : undefined;
      metrics[agent] = {
        summary: m.summary,
        durationMs: dur != null ? Math.max(dur, 1) : undefined,
      };
    }
  }
  return metrics;
}

export { agentLabel };
