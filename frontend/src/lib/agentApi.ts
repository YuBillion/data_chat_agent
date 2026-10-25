import type {
  AgentInfo,
  Intervention,
  ProblemDetail,
  RunEvent,
  RunResponse,
  SessionDetail,
  SessionSummary,
} from "../types/agent";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  problem?: ProblemDetail;
  status: number;

  constructor(status: number, message: string, problem?: ProblemDetail) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...options.headers,
  };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    credentials: "include",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });
  if (!response.ok) {
    let problem: ProblemDetail | undefined;
    try {
      problem = (await response.json()) as ProblemDetail;
    } catch {
      problem = undefined;
    }
    throw new ApiError(
      response.status,
      problem?.detail ?? `接口请求失败：HTTP ${response.status}`,
      problem,
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function listAgents(signal?: AbortSignal) {
  return request<AgentInfo[]>("/api/v1/agents", { signal });
}

export function createSession(title = "新会话", signal?: AbortSignal) {
  return request<SessionSummary>("/api/v1/sessions", {
    method: "POST",
    body: { title },
    signal,
  });
}

export function listSessions(limit = 30, signal?: AbortSignal) {
  return request<{ items: SessionSummary[]; next_cursor: string | null }>(
    `/api/v1/sessions?limit=${limit}`,
    { signal },
  );
}

export function getSession(sessionId: string, signal?: AbortSignal) {
  return request<SessionDetail>(`/api/v1/sessions/${sessionId}`, { signal });
}

export function deleteSession(sessionId: string, signal?: AbortSignal) {
  return request<void>(`/api/v1/sessions/${sessionId}`, {
    method: "DELETE",
    signal,
  });
}

export function createRun(
  sessionId: string,
  payload: { query: string; agent_id?: string | null },
  idempotencyKey: string,
  signal?: AbortSignal,
) {
  return request<RunResponse>(`/api/v1/sessions/${sessionId}/runs`, {
    method: "POST",
    body: payload,
    headers: { "Idempotency-Key": idempotencyKey },
    signal,
  });
}

export function getRun(runId: string, signal?: AbortSignal) {
  return request<RunResponse>(`/api/v1/runs/${runId}`, { signal });
}

export function cancelRun(runId: string, signal?: AbortSignal) {
  return request<RunResponse>(`/api/v1/runs/${runId}/cancel`, {
    method: "POST",
    signal,
  });
}

export function listInterventions(runId: string, signal?: AbortSignal) {
  return request<Intervention[]>(`/api/v1/runs/${runId}/interventions`, {
    signal,
  });
}

export function respondToIntervention(
  interventionId: string,
  payload: {
    expected_version: number;
    action: "select" | "approve" | "edit" | "reject";
    agent_id?: string;
    edited_sql?: string;
    reason?: string;
  },
  signal?: AbortSignal,
) {
  return request<Intervention>(
    `/api/v1/interventions/${interventionId}/respond`,
    {
      method: "POST",
      body: payload,
      signal,
    },
  );
}

export async function streamRunEvents(
  runId: string,
  options: {
    afterSeq: number;
    signal?: AbortSignal;
    onEvent: (event: RunEvent) => void;
  },
): Promise<number> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/runs/${runId}/events?after_seq=${options.afterSeq}`,
    {
      method: "GET",
      credentials: "include",
      headers: {
        Accept: "text/event-stream",
        "Last-Event-ID": String(options.afterSeq),
      },
      signal: options.signal,
    },
  );
  if (!response.ok) {
    throw new ApiError(response.status, `事件流连接失败：HTTP ${response.status}`);
  }
  if (!response.body) {
    throw new Error("浏览器未返回可读取的事件流。");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let seq = options.afterSeq;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const parsed = parseSse(part);
      if (!parsed) continue;
      if (parsed.id) seq = Math.max(seq, Number(parsed.id) || seq);
      if (parsed.event !== "heartbeat" && parsed.payload) {
        const runEvent = parsed.payload as unknown as RunEvent;
        seq = Math.max(seq, runEvent.seq ?? 0);
        options.onEvent(runEvent);
      }
    }
  }

  buffer += decoder.decode();
  const tail = parseSse(buffer);
  if (tail?.payload) {
    const runEvent = tail.payload as unknown as RunEvent;
    seq = Math.max(seq, runEvent.seq ?? 0);
    options.onEvent(runEvent);
  }
  return seq;
}

function parseSse(chunk: string): {
  id?: string;
  event?: string;
  payload?: unknown;
} | null {
  let id: string | undefined;
  let event: string | undefined;
  const dataLines: string[] = [];
  for (const line of chunk.split("\n")) {
    if (line.startsWith("id:")) id = line.slice(3).trim();
    else if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  if (dataLines.length === 0) return { id, event };
  try {
    return { id, event, payload: JSON.parse(dataLines.join("\n")) };
  } catch {
    return null;
  }
}
