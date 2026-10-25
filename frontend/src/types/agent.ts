export type RunStatus =
  | "queued"
  | "running"
  | "waiting_human"
  | "completed"
  | "rejected"
  | "failed"
  | "cancelled"
  | "expired";

export type AgentInfo = {
  agent_id: string;
  version: string;
  display_name: string;
  description: string;
  capabilities: string[];
  response_types: string[];
};

export type AgentOutput = {
  agent_id?: string;
  agent_version?: string;
  text?: string;
  sql?: string;
  columns?: string[];
  rows?: Array<Record<string, unknown>>;
  row_count?: number;
  truncated?: boolean;
  duration_ms?: number;
  references?: Array<{ type: string; id: string }>;
  limitations?: string[];
  confidence?: number;
  reason?: string;
  error_code?: string;
  status?: string;
};

export type RunResponse = {
  id: string;
  session_id: string;
  status: RunStatus;
  query: string;
  requested_agent_id: string | null;
  selected_agent_id: string | null;
  agent_version: string | null;
  route_mode: string | null;
  route_confidence: number | null;
  route: Record<string, unknown> | null;
  budget: Record<string, unknown>;
  output: AgentOutput | null;
  error_code: string | null;
  error_message: string | null;
  trace_id: string | null;
  version: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
};

export type SessionSummary = {
  id: string;
  title: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
};

export type SessionDetail = {
  session: SessionSummary;
  messages: Array<{
    id: string;
    run_id: string | null;
    role: "user" | "assistant";
    content: string;
    metadata: Record<string, unknown>;
    created_at: string;
  }>;
  runs: Array<{
    id: string;
    status: RunStatus;
    requested_agent_id: string | null;
    selected_agent_id: string | null;
    agent_version: string | null;
    route_mode: string | null;
    route_confidence: number | null;
    created_at: string;
    completed_at: string | null;
  }>;
};

export type Intervention = {
  id: string;
  run_id: string;
  kind: "agent_selection" | "sql_approval";
  status: "pending" | "responded" | "expired" | "cancelled";
  payload: {
    candidates?: Array<{
      agent_id: string;
      confidence: number;
      reason: string;
    }>;
    sql?: string;
    sql_hash?: string;
    tables?: string[];
    columns?: string[];
    estimated_rows?: number | null;
    risk_reasons?: string[];
    high_risk?: boolean;
    round?: number;
  };
  version: number;
  requested_at: string;
  expires_at: string;
  decision: string | null;
  actor_id: string | null;
  responded_at: string | null;
};

export type RunEvent = {
  schema_version: string;
  run_id: string;
  seq: number;
  trace_id: string | null;
  occurred_at: string;
  event_type: string;
  payload: Record<string, unknown>;
};

export type ProgressStatus = "running" | "success" | "error";

export type StepState = {
  step: string;
  status: ProgressStatus;
  updatedAt: number;
};

export type ChatMessage = {
  id: string;
  runId?: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
  status: "streaming" | "waiting" | "done" | "error";
  agentId?: string | null;
  steps?: StepState[];
  result?: AgentOutput;
  error?: string;
  intervention?: Intervention;
};

export type ProblemDetail = {
  title: string;
  status: number;
  detail: string;
  code: string;
  request_id: string;
  trace_id?: string | null;
  retryable?: boolean;
  details?: Record<string, unknown>;
};
