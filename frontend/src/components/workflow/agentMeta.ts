/** Static metadata for workflow graph cards — matches deterministic pipeline agents. */

export interface AgentCardMeta {
  order?: number;
  displayName: string;
  tasks: string[];
  type: 'source' | 'deterministic' | 'llm' | 'orchestrator' | 'agentic';
}

export const AGENT_META: Record<string, AgentCardMeta> = {
  connector: {
    displayName: 'Input Sources',
    tasks: ['Google Reviews', 'QR Feedback', 'Email Reports', 'Surveys'],
    type: 'source',
  },
  ingestion: {
    order: 1,
    displayName: 'IngestionAgent',
    tasks: ['Normalize', 'Dedup', 'Spam filter', 'PII redaction'],
    type: 'deterministic',
  },
  translation: {
    order: 2,
    displayName: 'TranslationAgent',
    tasks: ['Detect language', 'Translate to English', 'Retain originals'],
    type: 'deterministic',
  },
  scoring: {
    order: 3,
    displayName: 'ScoringAgent',
    tasks: ['Theme tagging', 'Sentiment score', 'Urgency flags'],
    type: 'deterministic',
  },
  clustering: {
    order: 4,
    displayName: 'ClusteringAgent',
    tasks: ['Group by site', 'Group by theme', 'Weekly buckets'],
    type: 'deterministic',
  },
  detection: {
    order: 5,
    displayName: 'DetectionAgent',
    tasks: ['Spike detection', 'Compounding signals', 'Priority ranking'],
    type: 'deterministic',
  },
  root_cause: {
    order: 6,
    displayName: 'RootCauseAgent',
    tasks: ['Keyword taxonomy', 'Evidence sampling', 'Category label'],
    type: 'deterministic',
  },
  sla: {
    order: 7,
    displayName: 'SLA Tracker',
    tasks: ['Response clocks', 'Breach warnings', 'Owner routing'],
    type: 'deterministic',
  },
  insight: {
    order: 8,
    displayName: 'InsightAgent',
    tasks: ['Draft recommendation', 'Suggest owner', 'Evidence grounding'],
    type: 'llm',
  },
  output: {
    order: 9,
    displayName: 'OutputAgent',
    tasks: ['Teams alerts', 'Digest queue', 'Site reports'],
    type: 'deterministic',
  },
  explainability: {
    order: 10,
    displayName: 'ExplainabilityAgent',
    tasks: ['Pipeline narrative', 'Decision rationale', 'Operator briefing'],
    type: 'deterministic',
  },
  orchestrator: {
    displayName: 'Orchestrator',
    tasks: ['Sequence stages', 'Emit triggers', 'Record lineage'],
    type: 'orchestrator',
  },
  assistant: {
    displayName: 'ConversationalAgent',
    tasks: ['User questions', 'ReAct tool loop', 'Grounded answers'],
    type: 'agentic',
  },
  investigator: {
    displayName: 'InvestigatorAgent',
    tasks: ['P1 auto-triage', 'Contagion check', 'Briefing draft'],
    type: 'agentic',
  },
  coordinator: {
    displayName: 'CoordinatorAgent',
    tasks: ['Pipeline runs', 'Tool routing', 'Branch on data'],
    type: 'agentic',
  },
  critic: {
    displayName: 'CriticAgent',
    tasks: ['Review drafts', 'Evidence check', 'Revise output'],
    type: 'agentic',
  },
  planner: {
    displayName: 'PlannerAgent',
    tasks: ['Plan retrieval', 'Tool selection', 'Step ordering'],
    type: 'llm',
  },
};

/** Canvas positions — spaced for larger agent cards */
export const WORKFLOW_LAYOUT: Record<string, { x: number; y: number }> = {
  connector: { x: 32, y: 200 },
  ingestion: { x: 268, y: 165 },
  translation: { x: 504, y: 165 },
  scoring: { x: 740, y: 165 },
  clustering: { x: 976, y: 165 },
  detection: { x: 1212, y: 165 },
  root_cause: { x: 1480, y: 72 },
  sla: { x: 1480, y: 268 },
  insight: { x: 1212, y: 400 },
  output: { x: 1480, y: 400 },
  explainability: { x: 1748, y: 400 },
  orchestrator: { x: 620, y: 24 },
};

export const CARD_W = 208;
export const CARD_H = 188;

export const PIPELINE_AGENT_IDS = [
  'connector', 'ingestion', 'translation', 'scoring', 'clustering',
  'detection', 'root_cause', 'sla', 'insight', 'output', 'explainability',
];

export type EdgeKind = 'pipeline' | 'trigger' | 'agentic';

export const WORKFLOW_EDGES: { from: string; to: string; kind: EdgeKind }[] = [
  { from: 'connector', to: 'ingestion', kind: 'pipeline' },
  { from: 'ingestion', to: 'translation', kind: 'pipeline' },
  { from: 'translation', to: 'scoring', kind: 'pipeline' },
  { from: 'scoring', to: 'clustering', kind: 'pipeline' },
  { from: 'clustering', to: 'detection', kind: 'pipeline' },
  { from: 'detection', to: 'root_cause', kind: 'trigger' },
  { from: 'detection', to: 'insight', kind: 'trigger' },
  { from: 'root_cause', to: 'sla', kind: 'trigger' },
  { from: 'insight', to: 'output', kind: 'pipeline' },
  { from: 'output', to: 'explainability', kind: 'pipeline' },
];

export function agentLabel(id: string): string {
  return AGENT_META[id]?.displayName ?? id.replace(/_/g, ' ');
}

export function typeDotColor(type: AgentCardMeta['type']): string {
  switch (type) {
    case 'llm': return '#a855f7';
    case 'agentic': return '#06b6d4';
    case 'orchestrator': return '#6366f1';
    case 'source': return '#3b82f6';
    default: return '#22c55e';
  }
}
