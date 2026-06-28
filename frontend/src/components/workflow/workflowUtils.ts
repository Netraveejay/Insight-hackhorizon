import type { A2AMessage } from '../../api';
import { WORKFLOW_EDGES, agentLabel, type EdgeKind } from './agentMeta';

export type FlowKind = 'pipeline' | 'trigger' | 'alert' | 'status' | 'agentic' | 'handoff';

export interface FlowStep {
  index: number;
  message: A2AMessage;
  kind: FlowKind;
  edgeKey: string | null;
  edgeKind: EdgeKind | null;
  fromAgent: string;
  toAgent: string | null;
  title: string;
  subtitle: string;
  phaseId: string;
}

export const FLOW_PHASES = [
  {
    id: 'start',
    label: 'Start',
    short: '1',
    description: 'Orchestrator kicks off the scheduled run',
    agents: ['orchestrator', 'connector'],
  },
  {
    id: 'ingest',
    label: 'Ingest & prepare',
    short: '2',
    description: 'Raw feedback is cleaned, deduped, and translated',
    agents: ['ingestion', 'translation'],
  },
  {
    id: 'analyze',
    label: 'Score & cluster',
    short: '3',
    description: 'Themes, sentiment, and site×theme clusters',
    agents: ['scoring', 'clustering', 'detection'],
  },
  {
    id: 'trigger',
    label: 'Triggered branches',
    short: '4',
    description: 'P1/P2 detections trigger root-cause, SLA, and insight',
    agents: ['root_cause', 'sla', 'insight'],
  },
  {
    id: 'output',
    label: 'Distribute',
    short: '5',
    description: 'Alerts, digests, and explainability narrative',
    agents: ['output', 'explainability'],
  },
] as const;

const EDGE_KIND_MAP = Object.fromEntries(
  WORKFLOW_EDGES.map((e) => [`${e.from}->${e.to}`, e.kind]),
) as Record<string, EdgeKind>;

export function edgeKindFor(from: string, to: string): EdgeKind | null {
  return EDGE_KIND_MAP[`${from}->${to}`] ?? null;
}

function phaseForAgent(agent: string): string {
  for (const p of FLOW_PHASES) {
    if ((p.agents as readonly string[]).includes(agent)) return p.id;
  }
  if (agent === 'orchestrator') return 'start';
  return 'analyze';
}

export function buildFlowSteps(messages: A2AMessage[]): FlowStep[] {
  return messages.map((m, index) => {
    const from = m.from_agent;
    const to = m.to_agent === 'broadcast' ? null : m.to_agent;
    const edgeKey = to && m.intent === 'handoff' ? `${from}->${to}` : null;
    const edgeKind = edgeKey ? edgeKindFor(from, to!) : null;

    let kind: FlowKind = 'handoff';
    if (m.intent === 'alert') kind = 'alert';
    else if (m.intent === 'status') kind = 'status';
    else if (edgeKind === 'trigger') kind = 'trigger';
    else if (edgeKind === 'agentic') kind = 'agentic';
    else if (edgeKind === 'pipeline') kind = 'pipeline';

    let title = '';
    let subtitle = m.summary;

    if (m.intent === 'alert') {
      title = `⚡ Alert from ${agentLabel(from)}`;
      subtitle = m.summary;
    } else if (m.intent === 'handoff' && to) {
      const triggerWord = edgeKind === 'trigger' ? 'TRIGGERS' : 'hands off to';
      title = `${agentLabel(from)} ${triggerWord} ${agentLabel(to)}`;
      subtitle = m.summary;
    } else if (m.intent === 'status' && m.status === 'processing') {
      title = `${agentLabel(from)} processing…`;
    } else if (m.intent === 'status' && m.status === 'done') {
      title = `${agentLabel(from)} complete`;
    } else {
      title = `${agentLabel(from)}${to ? ` → ${agentLabel(to)}` : ''}`;
    }

    const focusAgent = to && m.intent === 'handoff' ? to : from;

    return {
      index,
      message: m,
      kind,
      edgeKey,
      edgeKind,
      fromAgent: from,
      toAgent: to,
      title,
      subtitle,
      phaseId: phaseForAgent(focusAgent),
    };
  });
}

export function replayStatusAt(messages: A2AMessage[], upToIndex: number): Record<string, 'idle' | 'processing' | 'done' | 'error'> {
  const status: Record<string, 'idle' | 'processing' | 'done' | 'error'> = {};
  const slice = messages.slice(0, upToIndex + 1);
  for (const m of slice) {
    if (m.intent === 'status' && m.from_agent !== 'broadcast') {
      status[m.from_agent] = m.status === 'error' ? 'error' : m.status === 'done' ? 'done' : 'processing';
    }
    if (m.intent === 'handoff' && m.to_agent !== 'broadcast') {
      status[m.from_agent] = 'done';
      status[m.to_agent] = 'processing';
    }
  }
  for (const m of slice) {
    if (m.intent === 'status' && m.status === 'done' && m.from_agent !== 'broadcast') {
      status[m.from_agent] = 'done';
    }
  }
  return status;
}

export const SPEED_PRESETS = [
  { id: 'slow', label: 'Slow', ms: 2000 },
  { id: 'normal', label: 'Normal', ms: 1400 },
  { id: 'fast', label: 'Fast', ms: 700 },
] as const;
