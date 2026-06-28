const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}`
  : '/api';

let authToken: string | null = null;

function authHeaders(): Record<string, string> {
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  if (authToken) h.Authorization = `Bearer ${authToken}`;
  return h;
}

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...authHeaders(), ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(`API error ${detail}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  setToken: (token: string | null) => {
    authToken = token;
  },
  login: (username: string, password: string) =>
    fetchJson<{ token: string; user: AuthUser }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  me: () => fetchJson<AuthUser>('/auth/me'),
  downloadReport: async (reportId: string, fileName: string) => {
    const res = await fetch(`${API_BASE}/reports/${reportId}/download`, {
      headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
    });
    if (!res.ok) throw new Error('Download failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  },
  reports: (week?: string) =>
    fetchJson<{ reports: ReportMeta[] }>(`/reports${week ? `?week=${week}` : ''}`),
  overview: (week?: string) => fetchJson<OverviewData>(`/overview${week ? `?week=${week}` : ''}`),
  feed: (week?: string) => fetchJson<FeedData>(`/feed${week ? `?week=${week}` : ''}`),
  issues: (week?: string) => fetchJson<{ issues: Issue[] }>(`/issues${week ? `?week=${week}` : ''}`),
  issueDetail: (id: string) => fetchJson<IssueDetail>(`/issues/${id}`),
  trends: (week?: string) => fetchJson<Record<string, unknown>>(`/trends${week ? `?week=${week}` : ''}`),
  digest: (week?: string) => fetchJson<Record<string, unknown>>(`/digest${week ? `?week=${week}` : ''}`),
  leaderboard: (week?: string) =>
    fetchJson<LeaderboardData>(`/leaderboard${week ? `?week=${week}` : ''}`),
  summary: (month?: string) => fetchJson<Record<string, unknown>>(`/summary${month ? `?month=${month}` : ''}`),
  sites: () => fetchJson<{ sites: Site[] }>('/sites'),
  siteReport: (id: string, week?: string) =>
    fetchJson<Record<string, unknown>>(`/sites/${id}${week ? `?week=${week}` : ''}`),
  alerts: (week?: string) => fetchJson<AlertsData>(`/alerts${week ? `?week=${week}` : ''}`),
  connectors: () => fetchJson<ConnectorsStatus>('/connectors'),
  rules: () => fetchJson<Record<string, unknown>>('/rules'),
  rescore: (body: Record<string, unknown>) =>
    fetchJson<Record<string, unknown>>('/rules/rescore', { method: 'POST', body: JSON.stringify(body) }),
  ask: (question: string, week?: string) =>
    fetchJson<{ answer: string; references: string[] }>('/ask', {
      method: 'POST',
      body: JSON.stringify({ question, week }),
    }),
  assistantSuggestions: () => fetchJson<{ questions: string[] }>('/assistant/suggestions'),
  assistantStatus: () =>
    fetchJson<{ ai_enabled: boolean; mode: string; model: string | null; message: string }>('/assistant/status'),
  assistantChat: (messages: ChatMessage[], week?: string, correlationId?: string) =>
    fetchJson<AssistantChatResult>('/assistant/chat', {
      method: 'POST',
      body: JSON.stringify({ messages, week, correlation_id: correlationId }),
    }),
  assistantChatStream: async (
    messages: ChatMessage[],
    week?: string,
    correlationId?: string,
    onToken?: (token: string) => void,
  ): Promise<{ answer: string; references: AssistantReference[]; correlationId: string; mode?: string } | null> => {
    try {
      const res = await fetch(`${API_BASE}/assistant/chat/stream`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ messages, week, correlation_id: correlationId }),
      });
      if (!res.ok || !res.body) return null;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let answer = '';
      let references: AssistantReference[] = [];
      let cid = '';
      let mode: string | undefined;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          const data = JSON.parse(line.slice(6));
          if (data.type === 'meta') {
            references = data.references || [];
            cid = data.a2a_correlation_id || '';
            mode = data.mode;
          } else if (data.type === 'token') {
            answer += data.content;
            onToken?.(data.content);
          } else if (data.type === 'done' && data.answer) {
            answer = data.answer;
          }
        }
      }
      return { answer, references, correlationId: cid, mode };
    } catch {
      return null;
    }
  },
  agentRegistry: () =>
    fetchJson<{ agents: AgentDefinition[]; edges: { from: string; to: string }[] }>('/agents'),
  a2aMessages: (correlationId: string) =>
    fetchJson<{ correlation_id: string; messages: A2AMessage[] }>(`/a2a/messages?correlation_id=${correlationId}`),
  a2aCorrelations: () => fetchJson<{ correlation_ids: string[] }>('/a2a/correlations'),
  a2aRun: (week?: string) =>
    fetchJson<PipelineRunResult>(`/a2a/run${week ? `?week=${week}` : ''}`, { method: 'POST' }),
  runPipeline: (week?: string) =>
    fetchJson<PipelineRunResult>(`/pipeline/run${week ? `?week=${week}` : ''}`, { method: 'POST' }),
  pipelineRuns: () => fetchJson<{ runs: PipelineRunSummary[] }>('/pipeline/runs'),
  pipelineExplain: (week?: string) =>
    fetchJson<{ run_id: string; week: string; explanation: PipelineExplanation; a2a_correlation_id?: string }>(
      `/pipeline/explain${week ? `?week=${week}` : ''}`
    ),
  pipelineWorkflow: (week?: string) =>
    fetchJson<{ run_id: string; week: string; correlation_id: string; messages: A2AMessage[] }>(
      `/pipeline/workflow${week ? `?week=${week}` : ''}`
    ),
  agentRuns: (limit?: number) =>
    fetchJson<{ runs: AgentRunSummary[] }>(`/runs${limit ? `?limit=${limit}` : ''}`),
  agentRun: (runId: string) => fetchJson<AgentRunDetail>(`/runs/${runId}`),
  investigateRun: (clusterId: string, week?: string) =>
    fetchJson<{ run_id: string; run: AgentRunDetail }>('/runs/investigate', {
      method: 'POST',
      body: JSON.stringify({ cluster_id: clusterId, week }),
    }),
  agenticPipelineRun: (week?: string) =>
    fetchJson<PipelineRunResult>('/runs/pipeline', {
      method: 'POST',
      body: JSON.stringify({ week }),
    }),
};

export interface AlertsData {
  week: string;
  teams_webhook_configured: boolean;
  delivery_mode: string;
  description: string;
  alerts: {
    id: string;
    type: string;
    site_id: string;
    site_name: string;
    theme: string | null;
    theme_label: string | null;
    message: string;
    priority: string | null;
    delivered_to_teams: boolean;
    sla_status?: string | null;
    sla_label?: string | null;
    root_cause_summary?: string | null;
    created_at: string;
  }[];
}

export interface ConnectorsStatus {
  mode: string;
  teams_webhook_configured: boolean;
  connectors: {
    id: string;
    label: string;
    status: string;
    production_ready: boolean;
    description: string;
    config: string | null;
    configured: boolean;
    path?: string | null;
  }[];
}

export interface FeedData {
  week: string;
  has_data: boolean;
  pipeline: {
    total_received: number;
    active_in_feed: number;
    spam_removed: number;
    duplicates_removed: number;
    non_controllable: number;
    pii_redacted: number;
    translated: number;
  };
  active_items: {
    id: string;
    source_type: string;
    channel: string;
    channel_label: string;
    site_id: string;
    site_name: string;
    text: string;
    original_text?: string;
    original_language?: string;
    translated: boolean;
    rating: number | null;
    ts: string;
    is_spam: boolean;
    is_duplicate: boolean;
    pii_redacted: boolean;
    relevant: boolean;
    primary_theme?: string;
    sentiment?: Record<string, string>;
    status: string;
    filter_reason?: string | null;
  }[];
  filtered_items: FeedData['active_items'];
  source_coverage: { entries: { connector: string; status: string; item_count: number; message: string }[] };
}

export interface AuthUser {
  username: string;
  role: string;
  name: string;
  email: string;
  site_id: string | null;
}

export interface ReportMeta {
  id: string;
  week: string;
  report_type: string;
  site_id: string | null;
  title: string;
  recipient_email: string;
  file_name: string;
  created_at: string | null;
}

export interface PipelineStep {
  id: string;
  label: string;
  detail: string;
  count: number;
  status: string;
}

export interface PipelineRunResult {
  run_id: string;
  week: string;
  items_ingested: number;
  items_translated: number;
  items_scored: number;
  clusters: number;
  detections: number;
  insights: number;
  rules_version: string;
  steps: PipelineStep[];
  hero_cluster_id: string | null;
  outputs: { type: string; label: string; count: number }[];
  explanation?: PipelineExplanation | null;
  a2a_correlation_id?: string | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  references?: AssistantReference[];
}

export interface AssistantReference {
  cluster_id: string;
  site_id: string;
  site_name: string;
  theme: string;
  week: string;
  label: string;
}

export interface AssistantChatResult {
  answer: string;
  references: AssistantReference[];
  a2a_correlation_id: string;
  tools_used: string[];
  mode?: string;
}

export interface AgentDefinition {
  id: string;
  name: string;
  type: string;
  role: string;
  layout_x: number;
  layout_y: number;
}

export interface A2AMessage {
  id: string;
  ts: string;
  correlation_id: string;
  from_agent: string;
  to_agent: string;
  intent: string;
  summary: string;
  status: string;
  payload_ref: string | null;
}

export interface StepExplanation {
  id: string;
  label: string;
  what_happened: string;
  why_it_matters: string;
  input_label: string;
  output_label: string;
  highlights: string[];
}

export interface HeroExplanation {
  cluster_id: string;
  site_name: string;
  theme_label: string;
  priority: string;
  headline: string;
  story: string;
  reasons: string[];
  next_views: string[];
}

export interface PipelineExplanation {
  headline: string;
  summary: string;
  audience_note: string;
  steps: StepExplanation[];
  hero: HeroExplanation | null;
  glossary: Record<string, string>;
}

export interface PipelineRunSummary {
  id: string;
  cadence: string;
  week: string;
  rules_version: string;
  status: string;
  stats: Record<string, unknown>;
  started_at: string | null;
}

export interface AgentMessage {
  id: string;
  seq: number;
  from_agent: string;
  to_agent: string;
  from_label: string;
  to_label: string;
  message_type: 'request' | 'response' | 'enrichment' | string;
  subject: string;
  artifact_type: string;
  artifact_count: number;
  payload_summary: Record<string, unknown>;
  sample: Record<string, unknown>[];
  timestamp: string;
}

export interface AgentWorkflow {
  run_id: string;
  week: string;
  protocol: string;
  agents: string[];
  messages: AgentMessage[];
  summary: string;
}

export interface AgentTrigger {
  id: string;
  type: 'schedule' | 'detection' | 'anomaly' | 'question' | 'manual';
  source: string;
  summary: string;
  ts: string;
  payload: Record<string, unknown>;
}

export interface ReasoningStep {
  run_id: string;
  step_no: number;
  agent: string;
  phase: 'think' | 'act' | 'observe' | 'reflect' | 'final';
  thought: string;
  action?: { tool: string; input: Record<string, unknown> } | null;
  observation?: string | null;
  ts: string;
}

export interface AgentRunSummary {
  id: string;
  goal: string;
  runner: string;
  status: string;
  outcome: string | null;
  started_at: string;
  ended_at: string | null;
  trigger: AgentTrigger | null;
}

export interface AgentRunDetail extends AgentRunSummary {
  correlation_id: string;
  steps: ReasoningStep[];
}

export interface Site {
  id: string;
  name: string;
  email: string;
}

export interface OverviewData {
  week: string;
  weighted_csat_pct: number;
  open_issues: number;
  cross_source_flags: number;
  items_processed: number;
  ranked_actions: RankedAction[];
  positive_themes: [string, number][];
  hero_issue: RankedAction | null;
  language_mix?: { language: string; count: number; translated: number }[];
  sla_summary?: { on_track: number; at_risk: number; breached: number };
}

export interface RankedAction {
  cluster_id: string;
  site_id: string;
  site_name: string;
  theme: string;
  priority: string;
  neg: number;
  insight?: string;
  flags?: string[];
  root_cause_summary?: string | null;
  sla_status?: string | null;
  sla_label?: string | null;
}

export interface RootCause {
  category: string;
  summary: string;
  contributing_factors: string[];
  confidence: string;
  evidence_keywords?: string[];
}

export interface SlaInfo {
  priority: string;
  status: string;
  phase: string;
  label: string;
  response_hours: number;
  resolution_hours: number;
  hours_to_response: number;
  hours_to_resolution: number;
  triggered_at: string;
  response_due_at: string;
  resolution_due_at: string;
}

export interface IssueDetail {
  cluster_id: string;
  site_id: string;
  site_name: string;
  theme: string;
  theme_label: string;
  week: string;
  volume: number;
  neg: number;
  pos: number;
  confidence_band: string;
  source_type: string;
  priority: string;
  signals: { type: string; label: string; description: string }[];
  root_cause?: RootCause | null;
  sla?: SlaInfo | null;
  recommendation: {
    text: string | null;
    owner: string | null;
    status: string | null;
    draft_source: string | null;
  };
  evidence: {
    id: string;
    text: string;
    original_text: string;
    original_language: string;
    translated: boolean;
    channel: string;
    channel_label: string;
    source_type: string;
    rating: number | null;
    sentiment: string;
    urgency: string;
    ts: string;
    timeline: { stage: string; detail: string; rules_version?: string }[];
  }[];
  evidence_count: number;
}

export interface Issue {
  cluster_id: string;
  site_id: string;
  site_name: string;
  theme: string;
  week: string;
  volume: number;
  neg: number;
  pos: number;
  confidence_band: string;
  priority: string;
  flags: { cross_source: boolean; compounding: boolean; spike: boolean };
  insight_preview?: string;
  root_cause_summary?: string | null;
  sla_status?: string | null;
}

export interface LeaderboardSite {
  site_id: string;
  site_name: string;
  efficiency_score: number;
  sla_compliance_pct: number;
  issue_handling_pct: number;
  csat_pct: number;
  improvement_pct: number;
  open_p1: number;
  open_p2: number;
  open_issues: number;
}

export interface LeaderboardEntry {
  rank: number;
  theatre_id: string;
  theatre_name: string;
  region: string;
  site_count: number;
  sites: LeaderboardSite[];
  efficiency_score: number;
  sla_compliance_pct: number;
  issue_handling_pct: number;
  csat_pct: number;
  improvement_pct: number;
  open_p1: number;
  open_p2: number;
  open_issues: number;
  badge: 'top' | null;
}

export interface LeaderboardData {
  week: string;
  prior_week: string | null;
  top_theatre_id: string | null;
  top_theatre_name: string | null;
  methodology: string;
  entries: LeaderboardEntry[];
  total_theatres: number;
  total_sites: number;
}
