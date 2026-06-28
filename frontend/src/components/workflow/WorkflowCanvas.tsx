import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AGENT_META,
  PIPELINE_AGENT_IDS,
  WORKFLOW_EDGES,
  type EdgeKind,
} from './agentMeta';
import AgentPersona from './AgentPersona';
import {
  CANVAS_H,
  CANVAS_W,
  PERSONA_H,
  PERSONA_LAYOUT,
  PERSONA_W,
  agentAnchorBottom,
  agentAnchorLeft,
  agentAnchorRight,
  agentAnchorTop,
  agentCenter,
} from './personaLayout';
import type { A2AMessage } from '../../api';

export interface NodeMetrics {
  summary?: string;
  durationMs?: number;
}

interface Props {
  nodeStatus: Record<string, 'idle' | 'processing' | 'done' | 'error'>;
  nodeMetrics: Record<string, NodeMetrics>;
  activeEdge: string | null;
  activeEdgeKind: EdgeKind | null;
  highlightedNode: string | null;
  completedEdges: Set<string>;
  edgeLabels: Record<string, string>;
  totalItems?: number;
}

function routeEdge(from: string, to: string, _kind: EdgeKind): string {
  const layout = PERSONA_LAYOUT;
  const a = layout[from];
  const b = layout[to];
  if (!a || !b) return '';

  const sameRow = Math.abs(a.y - b.y) < 80;
  const bBelow = b.y > a.y + 100;
  const bAbove = b.y < a.y - 100;

  let x1: number, y1: number, x2: number, y2: number;

  if (sameRow) {
    const left = a.x < b.x ? from : to;
    const right = left === from ? to : from;
    const p1 = agentAnchorRight(left, layout);
    const p2 = agentAnchorLeft(right, layout);
    x1 = p1.x; y1 = p1.y; x2 = p2.x; y2 = p2.y;
    const mx = (x1 + x2) / 2;
    return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
  }

  if (bBelow) {
    const p1 = agentAnchorBottom(from, layout);
    const p2 = agentAnchorTop(to, layout);
    x1 = p1.x; y1 = p1.y; x2 = p2.x; y2 = p2.y;
    const my = (y1 + y2) / 2;
    return `M ${x1} ${y1} C ${x1} ${my}, ${x2} ${my}, ${x2} ${y2}`;
  }

  if (bAbove) {
    const p1 = agentAnchorTop(from, layout);
    const p2 = agentAnchorBottom(to, layout);
    x1 = p1.x; y1 = p1.y; x2 = p2.x; y2 = p2.y;
    const my = (y1 + y2) / 2;
    return `M ${x1} ${y1} C ${x1} ${my}, ${x2} ${my}, ${x2} ${y2}`;
  }

  const c1 = agentCenter(from, layout);
  const c2 = agentCenter(to, layout);
  const mx = (c1.cx + c2.cx) / 2;
  return `M ${c1.cx} ${c1.cy} C ${mx} ${c1.cy}, ${mx} ${c2.cy}, ${c2.cx} ${c2.cy}`;
}

function edgeMidpoint(path: string): { x: number; y: number } {
  const nums = path.match(/[\d.]+/g)?.map(Number) ?? [0, 0];
  if (nums.length >= 4) {
    return { x: (nums[0] + nums[nums.length - 2]) / 2, y: (nums[1] + nums[nums.length - 1]) / 2 };
  }
  return { x: 0, y: 0 };
}

export default function WorkflowCanvas({
  nodeStatus,
  nodeMetrics,
  activeEdge,
  activeEdgeKind,
  highlightedNode,
  completedEdges,
  edgeLabels,
  totalItems,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const visibleIds = useMemo(() => new Set([...PIPELINE_AGENT_IDS]), []);

  const edges = WORKFLOW_EDGES.filter(({ from, to }) => visibleIds.has(from) && PERSONA_LAYOUT[from] && PERSONA_LAYOUT[to]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const update = () => {
      const w = el.clientWidth;
      if (w <= 0) return;
      setScale(w / CANVAS_W);
    };

    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div
      ref={containerRef}
      className="relative bg-[#070b14] w-full overflow-hidden"
      style={{ aspectRatio: `${CANVAS_W} / ${CANVAS_H}` }}
    >
      <div
        className="absolute inset-0 flex justify-center"
      >
        <div
          className="relative"
          style={{
            width: CANVAS_W,
            height: CANVAS_H,
            transform: `scale(${scale})`,
            transformOrigin: 'top center',
          }}
        >
      {/* Starfield */}
      <div
        className="absolute inset-0 opacity-30 pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(1px 1px at 20px 30px, #fff, transparent), radial-gradient(1px 1px at 80px 120px, #94a3b8, transparent), radial-gradient(1.5px 1.5px at 200px 80px, #fff, transparent)',
          backgroundSize: '320px 200px',
        }}
      />

      <div className="relative" style={{ width: CANVAS_W, height: CANVAS_H }}>
        <svg
          className="absolute inset-0 pointer-events-none"
          width={CANVAS_W}
          height={CANVAS_H}
          viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
        >
          <defs>
            <marker id="arr-flow" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto">
              <path d="M0,0 L8,4 L0,8 Z" fill="#3b82f6" opacity="0.8" />
            </marker>
            <marker id="arr-trigger" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto">
              <path d="M0,0 L8,4 L0,8 Z" fill="#f59e0b" />
            </marker>
            <marker id="arr-active" markerWidth="12" markerHeight="12" refX="9" refY="5" orient="auto">
              <path d="M0,0 L9,5 L0,10 Z" fill="#93c5fd" />
            </marker>
            <filter id="edge-glow">
              <feGaussianBlur stdDeviation="3" result="b" />
              <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          {edges.map(({ from, to, kind }) => {
            const key = `${from}->${to}`;
            const active = activeEdge === key;
            const done = completedEdges.has(key);
            const path = routeEdge(from, to, kind);
            const mid = edgeMidpoint(path);
            const label = edgeLabels[key];

            return (
              <g key={key}>
                <path
                  d={path}
                  fill="none"
                  stroke={active ? '#60a5fa' : kind === 'trigger' ? '#d97706' : '#334155'}
                  strokeWidth={active ? 4 : done ? 2.5 : 2}
                  strokeDasharray={kind === 'trigger' ? '10 7' : undefined}
                  markerEnd={active ? 'url(#arr-active)' : kind === 'trigger' ? 'url(#arr-trigger)' : 'url(#arr-flow)'}
                  opacity={active ? 1 : done ? 0.7 : 0.45}
                  strokeLinecap="round"
                  filter={active ? 'url(#edge-glow)' : undefined}
                  className={active ? 'animate-pulse' : ''}
                />
                {label && done && (
                  <g>
                    <rect x={mid.x - 62} y={mid.y - 13} width={124} height={22} rx={5} fill="#0f172a" opacity={0.92} stroke="#334155" strokeWidth={0.5} />
                    <text x={mid.x} y={mid.y + 4} textAnchor="middle" className="fill-slate-200 text-[11px] font-mono">
                      {label.length > 20 ? `${label.slice(0, 18)}…` : label}
                    </text>
                  </g>
                )}
                {active && kind === 'trigger' && (
                  <text x={mid.x} y={mid.y - 20} textAnchor="middle" className="fill-amber-300 text-[11px] font-bold">
                    ⚡ TRIGGER
                  </text>
                )}
              </g>
            );
          })}

          {activeEdge && (() => {
            const [from, to] = activeEdge.split('->');
            const path = routeEdge(from, to, activeEdgeKind ?? 'pipeline');
            return (
              <circle r="5" fill="#93c5fd">
                <animateMotion dur="2.2s" repeatCount="indefinite" path={path} />
              </circle>
            );
          })()}
        </svg>

        {Array.from(visibleIds).map((id) => {
          const pos = PERSONA_LAYOUT[id];
          const meta = AGENT_META[id];
          if (!pos || !meta) return null;
          return (
            <div
              key={id}
              className="absolute"
              style={{ left: pos.x, top: pos.y, width: PERSONA_W, height: PERSONA_H }}
            >
              <AgentPersona
                id={id}
                meta={meta}
                status={nodeStatus[id] || 'idle'}
                metric={nodeMetrics[id]?.summary}
                highlighted={highlightedNode === id}
                totalItems={id === 'connector' ? totalItems : undefined}
              />
            </div>
          );
        })}
      </div>
        </div>
      </div>
    </div>
  );
}

export function buildNodeMetrics(messages: A2AMessage[]): Record<string, NodeMetrics> {
  const metrics: Record<string, NodeMetrics> = {};
  const started: Record<string, number> = {};
  for (const m of messages) {
    const ts = new Date(m.ts).getTime();
    if (m.intent === 'handoff' && m.to_agent !== 'broadcast') started[m.to_agent] = ts;
    if (m.intent === 'status' && m.status === 'processing' && m.from_agent !== 'broadcast') {
      started[m.from_agent] = started[m.from_agent] ?? ts;
    }
    if (m.intent === 'status' && m.status === 'done' && m.from_agent !== 'broadcast') {
      const agent = m.from_agent;
      metrics[agent] = {
        summary: m.summary,
        durationMs: started[agent] ? Math.max(ts - started[agent], 1) : undefined,
      };
    }
  }
  return metrics;
}

export function buildEdgeLabels(messages: A2AMessage[]): Record<string, string> {
  const labels: Record<string, string> = {};
  for (const m of messages) {
    if (m.intent === 'handoff' && m.to_agent !== 'broadcast') {
      const key = `${m.from_agent}->${m.to_agent}`;
      const short = m.summary.length > 22 ? m.summary.slice(0, 20) + '…' : m.summary;
      labels[key] = short;
    }
  }
  return labels;
}

export { agentLabel } from './agentMeta';
