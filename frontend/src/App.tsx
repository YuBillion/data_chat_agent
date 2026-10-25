import {
  Activity,
  BarChart3,
  Bot,
  Eraser,
  History,
  Leaf,
  MessageSquarePlus,
  Server,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { AgentPicker } from "./components/AgentPicker";
import { Composer } from "./components/Composer";
import { EmptyState } from "./components/EmptyState";
import { MessageBubble } from "./components/MessageBubble";
import {
  ApiError,
  cancelRun,
  createRun,
  createSession,
  deleteSession,
  getRun,
  getSession,
  listAgents,
  listInterventions,
  listSessions,
  respondToIntervention,
  streamRunEvents,
} from "./lib/agentApi";
import { cn, summarizeResult } from "./lib/format";
import type {
  AgentInfo,
  AgentOutput,
  ChatMessage,
  Intervention,
  RunEvent,
  RunStatus,
  SessionSummary,
  StepState,
} from "./types/agent";

const examples = [
  "统计 2025 年第一季度各大区的 GMV，并按 GMV 从高到低排序",
  "GMV 的统计口径是什么？",
  "统计 2025 年 3 月各商品品类的销量和销售额",
  "查询华东地区 2025 年第一季度销售额最高的前 5 个商品",
];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "同源 /api";
const terminalStatuses = new Set<RunStatus>([
  "completed",
  "rejected",
  "failed",
  "cancelled",
  "expired",
]);

function makeId() {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function upsertStep(
  steps: StepState[] = [],
  step: string,
  status: "running" | "success" | "error",
) {
  const next = steps.filter((item) => item.step !== step);
  next.push({ step, status, updatedAt: Date.now() });
  return next;
}

function eventOutput(event: RunEvent): AgentOutput | undefined {
  const output = event.payload.output;
  if (output && typeof output === "object") return output as AgentOutput;
  const data = event.payload.data;
  if (data && typeof data === "object") return data as AgentOutput;
  return undefined;
}

function asIntervention(event: RunEvent): Intervention | undefined {
  if (event.event_type !== "agent.selection_required" && event.event_type !== "sql.approval_required") {
    return undefined;
  }
  const inner = event.payload.payload;
  if (!inner || typeof inner !== "object") return undefined;
  const payload = inner as Intervention["payload"];
  return {
    id: String(event.payload.intervention_id),
    run_id: event.run_id,
    kind: event.event_type === "agent.selection_required" ? "agent_selection" : "sql_approval",
    status: "pending",
    payload,
    version: Number(event.payload.version),
    requested_at: event.occurred_at,
    expires_at: String(event.payload.expires_at),
    decision: null,
    actor_id: null,
    responded_at: null,
  };
}

export default function App() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [activeController, setActiveController] = useState<AbortController | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [loadingSession, setLoadingSession] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const isStreaming = Boolean(activeController);
  const hasPendingIntervention = messages.some(
    (message) => message.status === "waiting",
  );
  const canSubmit =
    draft.trim().length > 0 &&
    !isStreaming &&
    !loadingSession &&
    !hasPendingIntervention;
  const completedCount = useMemo(
    () => messages.filter((message) => message.role === "assistant" && message.status === "done").length,
    [messages],
  );
  const currentSession = sessions.find((session) => session.id === currentSessionId);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([listAgents(controller.signal), listSessions(30, controller.signal)])
      .then(([agentItems, sessionPage]) => {
        setAgents(agentItems);
        setSessions(sessionPage.items);
        if (sessionPage.items[0]) {
          void openSession(sessionPage.items[0].id, controller.signal);
        }
      })
      .catch((error) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setGlobalError(error instanceof Error ? error.message : String(error));
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  async function refreshSessions(signal?: AbortSignal) {
    try {
      const page = await listSessions(30, signal);
      setSessions(page.items);
    } catch {
      // The active run still provides enough local context if history refresh fails.
    }
  }

  async function openSession(sessionId: string, signal?: AbortSignal) {
    if (isStreaming) return;
    setLoadingSession(true);
    setGlobalError(null);
    try {
      const detail = await getSession(sessionId, signal);
      setCurrentSessionId(sessionId);
      const restored: ChatMessage[] = detail.messages.map((message) => ({
          id: message.id,
          runId: message.run_id ?? undefined,
          role: message.role,
          content: message.content,
          createdAt: Date.parse(message.created_at),
          status: "done",
      }));
      const pendingRuns = detail.runs.filter(
        (run) => run.status === "waiting_human",
      );
      await Promise.all(
        pendingRuns.map(async (run) => {
          const interventions = await listInterventions(run.id, signal);
          const pending = [...interventions]
            .reverse()
            .find((item) => item.status === "pending");
          if (!pending) return;
          let assistant = restored.find(
            (message) => message.role === "assistant" && message.runId === run.id,
          );
          if (!assistant) {
            assistant = {
              id: makeId(),
              runId: run.id,
              role: "assistant",
              content:
                pending.kind === "agent_selection"
                  ? "自动路由需要你确认使用哪个 Agent。"
                  : "SQL 已生成，等待人工审批。",
              createdAt: Date.parse(run.created_at),
              status: "waiting",
              agentId: run.selected_agent_id,
              steps: upsertStep(
                [],
                pending.kind === "agent_selection" ? "选择 Agent" : "SQL审批",
                "running",
              ),
            };
            restored.push(assistant);
          }
          assistant.status = "waiting";
          assistant.intervention = pending;
        }),
      );
      const completedRuns = detail.runs
        .filter((run) => run.status === "completed")
        .slice(0, 10);
      await Promise.all(
        completedRuns.map(async (run) => {
          const fullRun = await getRun(run.id, signal);
          const assistant = restored.find(
            (message) => message.role === "assistant" && message.runId === run.id,
          );
          if (assistant && fullRun.output) {
            assistant.result = fullRun.output;
            assistant.content = fullRun.output.text || assistant.content;
            assistant.agentId = fullRun.output.agent_id ?? run.selected_agent_id;
          }
        }),
      );
      setMessages(restored);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        setGlobalError(error instanceof Error ? error.message : String(error));
      }
    } finally {
      setLoadingSession(false);
    }
  }

  function newConversation() {
    if (isStreaming) return;
    setCurrentSessionId(null);
    setMessages([]);
    setDraft("");
    setGlobalError(null);
  }

  async function startQuery(rawQuery = draft) {
    const query = rawQuery.trim();
    if (!query || isStreaming || loadingSession) return;

    setGlobalError(null);
    setDraft("");
    const controller = new AbortController();
    const assistantId = makeId();
    setActiveController(controller);
    try {
      let sessionId = currentSessionId;
      if (!sessionId) {
        const session = await createSession(query.slice(0, 80), controller.signal);
        sessionId = session.id;
        setCurrentSessionId(session.id);
        setSessions((current) => [session, ...current.filter((item) => item.id !== session.id)]);
      }
      const run = await createRun(
        sessionId,
        { query, agent_id: selectedAgentId || null },
        makeId(),
        controller.signal,
      );
      setActiveRunId(run.id);
      setMessages((current) => [
        ...current,
        {
          id: makeId(),
          runId: run.id,
          role: "user",
          content: query,
          createdAt: Date.now(),
          status: "done",
        },
        {
          id: assistantId,
          runId: run.id,
          role: "assistant",
          content: "正在连接 Agent Harness…",
          createdAt: Date.now(),
          status: "streaming",
          steps: upsertStep([], "提交运行", "success"),
        },
      ]);
      await watchRun(run.id, assistantId, controller);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      const message = error instanceof ApiError ? error.message : error instanceof Error ? error.message : String(error);
      setGlobalError(message);
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantId
            ? { ...item, status: "error", content: "本次运行没有成功。", error: message }
            : item,
        ),
      );
    } finally {
      setActiveController(null);
      setActiveRunId(null);
      await refreshSessions();
    }
  }

  async function watchRun(
    runId: string,
    assistantId: string,
    controller: AbortController,
  ) {
    let cursor = 0;
    let finished = false;
    let failures = 0;
    while (!finished && !controller.signal.aborted && failures < 5) {
      try {
        cursor = await streamRunEvents(runId, {
          afterSeq: cursor,
          signal: controller.signal,
          onEvent: (event) => {
            if (
              event.event_type === "run.completed" ||
              event.event_type === "run.failed" ||
              event.event_type === "run.rejected" ||
              event.event_type === "run.cancelled" ||
              event.event_type === "run.expired"
            ) {
              finished = true;
            }
            if (event.event_type !== "heartbeat") {
              setMessages((current) =>
                current.map((message) =>
                  message.id === assistantId
                    ? applyEvent(message, event)
                    : message,
                ),
              );
            }
          },
        });
        failures = 0;
        if (!finished) {
          const run = await getRun(runId, controller.signal);
          if (terminalStatuses.has(run.status)) break;
          await new Promise((resolve) => window.setTimeout(resolve, 500));
        }
      } catch (error) {
        if (controller.signal.aborted) throw error;
        failures += 1;
        if (failures >= 5) throw error;
        await new Promise((resolve) => window.setTimeout(resolve, Math.min(1000 * 2 ** failures, 8000)));
      }
    }
    const finalRun = await getRun(runId, controller.signal);
    setMessages((current) =>
      current.map((message) => {
        if (message.id !== assistantId) return message;
        if (finalRun.status === "completed" && finalRun.output) {
          return message.status === "done"
            ? message
            : {
                ...message,
                status: "done",
                content: finalRun.output.text || summarizeResult(finalRun.output.rows),
                result: finalRun.output,
              };
        }
        if (finalRun.status === "waiting_human") return { ...message, status: "waiting" };
        if (finalRun.status === "cancelled") {
          return { ...message, status: "done", content: "已停止本次运行。" };
        }
        if (terminalStatuses.has(finalRun.status)) {
          return {
            ...message,
            status: "error",
            content: "本次运行没有成功。",
            error: finalRun.error_message || finalRun.error_code || finalRun.status,
          };
        }
        return message;
      }),
    );
  }

  async function stopQuery() {
    if (!activeController) return;
    if (activeRunId) {
      try {
        await cancelRun(activeRunId);
      } catch {
        // Local cancellation still releases the browser connection.
      }
    }
    activeController.abort();
  }

  async function handleIntervention(
    message: ChatMessage,
    decision: {
      action: "select" | "approve" | "edit" | "reject";
      agentId?: string;
      editedSql?: string;
      reason?: string;
    },
  ) {
    if (!message.intervention || !message.runId) return;
    const record = await respondToIntervention(message.intervention.id, {
      expected_version: message.intervention.version,
      action: decision.action,
      agent_id: decision.agentId,
      edited_sql: decision.editedSql,
      reason: decision.reason,
    });
    setMessages((current) =>
      current.map((item) =>
        item.id === message.id
          ? {
              ...item,
              status: decision.action === "reject" ? "done" : "streaming",
              intervention: { ...record },
              content:
                decision.action === "select"
                  ? `已选择 ${agents.find((agent) => agent.agent_id === decision.agentId)?.display_name ?? decision.agentId}，正在恢复运行…`
                  : decision.action === "reject"
                    ? "已拒绝 SQL 执行。"
                    : "审批已提交，正在恢复运行…",
            }
          : item,
      ),
    );
    if (
      decision.action !== "reject" &&
      !(activeController && activeRunId === message.runId)
    ) {
      const controller = new AbortController();
      setActiveController(controller);
      setActiveRunId(message.runId);
      void watchRun(message.runId, message.id, controller).finally(() => {
        setActiveController(null);
        setActiveRunId(null);
        void refreshSessions();
      });
    }
  }

  async function removeSession(sessionId: string) {
    if (isStreaming) return;
    try {
      await deleteSession(sessionId);
      setSessions((current) => current.filter((item) => item.id !== sessionId));
      if (currentSessionId === sessionId) newConversation();
    } catch (error) {
      setGlobalError(error instanceof Error ? error.message : String(error));
    }
  }

  return (
    <div className="h-dvh overflow-hidden bg-parchment text-ink">
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(90deg,rgba(32,32,29,0.045)_1px,transparent_1px),linear-gradient(rgba(32,32,29,0.035)_1px,transparent_1px)] bg-[size:48px_48px]" />
      <div className="pointer-events-none fixed inset-0 grain" />

      <div className="relative grid h-full min-h-0 overflow-hidden lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="hidden min-h-0 border-r border-ink/10 bg-[#efe6d8]/85 backdrop-blur lg:flex lg:flex-col">
          <div className="border-b border-ink/10 px-5 py-5">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center bg-ink text-parchment">
                <BarChart3 className="h-5 w-5" />
              </div>
              <div>
                <div className="text-base font-semibold tracking-[0.02em]">智能问数</div>
                <div className="text-xs text-ink/50">multi-agent harness</div>
              </div>
            </div>
          </div>

          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-4">
            <button
              type="button"
              onClick={newConversation}
              disabled={isStreaming}
              className="flex h-11 w-full items-center justify-center gap-2 bg-ink text-sm font-semibold text-parchment transition hover:bg-soot disabled:cursor-not-allowed disabled:bg-ink/35"
            >
              <MessageSquarePlus className="h-4 w-4" />
              新会话
            </button>

            <section>
              <div className="mb-2 flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
                <History className="h-3.5 w-3.5" />
                会话
              </div>
              <div className="space-y-1">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    className={cn(
                      "group flex items-center border",
                      currentSessionId === session.id
                        ? "border-moss/30 bg-moss/10"
                        : "border-transparent hover:border-ink/10 hover:bg-white/40",
                    )}
                  >
                    <button
                      type="button"
                      disabled={isStreaming}
                      onClick={() => void openSession(session.id)}
                      className="min-w-0 flex-1 truncate px-3 py-2 text-left text-sm text-ink/75 disabled:opacity-50"
                    >
                      {session.title}
                    </button>
                    <button
                      type="button"
                      disabled={isStreaming}
                      onClick={() => void removeSession(session.id)}
                      className="mr-1 rounded p-1.5 text-ink/30 opacity-0 hover:bg-tomato/10 hover:text-tomato group-hover:opacity-100 disabled:hidden"
                      aria-label={`删除会话 ${session.title}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
                {sessions.length === 0 && (
                  <p className="px-1 py-2 text-xs leading-5 text-ink/40">暂无历史会话</p>
                )}
              </div>
            </section>

            <section>
              <div className="mb-2 flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
                <Bot className="h-3.5 w-3.5" />
                样例
              </div>
              <div className="space-y-2">
                {examples.map((example) => (
                  <button
                    key={example}
                    type="button"
                    disabled={isStreaming}
                    onClick={() => setDraft(example)}
                    className="w-full border border-ink/10 bg-white/42 px-3 py-3 text-left text-sm leading-5 text-ink/75 transition hover:border-moss/35 hover:bg-white/75 disabled:cursor-not-allowed disabled:opacity-55"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </section>
          </div>

          <div className="border-t border-ink/10 p-4">
            <div className="grid gap-2 text-xs text-ink/55">
              <div className="flex items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2">
                  <Server className="h-3.5 w-3.5" />
                  API
                </span>
                <span className="truncate font-mono">{API_BASE_URL}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2">
                  <Activity className="h-3.5 w-3.5" />
                  完成
                </span>
                <span>{completedCount}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Agent 注册</span>
                <span>{agents.length}</span>
              </div>
            </div>
          </div>
        </aside>

        <main className="flex min-h-0 min-w-0 flex-col overflow-hidden">
          <header className="flex h-16 shrink-0 items-center justify-between border-b border-ink/10 bg-parchment/88 px-4 backdrop-blur lg:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <div className="grid h-9 w-9 shrink-0 place-items-center bg-moss text-white lg:hidden">
                <BarChart3 className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-ink">
                  {currentSession?.title ?? "智能数据分析 Agent"}
                </div>
                <div className="truncate text-xs text-ink/45">
                  FastAPI · LangGraph · PostgreSQL/Redis
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={newConversation}
              disabled={isStreaming || messages.length === 0}
              className="grid h-9 w-9 place-items-center rounded-full text-ink/55 transition hover:bg-ink/5 hover:text-ink disabled:cursor-not-allowed disabled:opacity-35"
              title="清空当前视图"
              aria-label="清空当前视图"
            >
              <Eraser className="h-4 w-4" />
            </button>
          </header>

          {globalError && (
            <div className="border-b border-tomato/20 bg-tomato/10 px-4 py-2 text-sm text-tomato">
              {globalError}
            </div>
          )}

          <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            {messages.length === 0 ? (
              <EmptyState examples={examples} onUseExample={(example) => setDraft(example)} />
            ) : (
              <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 lg:px-8">
                {messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    agents={agents}
                    onInterventionRespond={handleIntervention}
                  />
                ))}
              </div>
            )}
          </div>

          <div className="border-t border-ink/10 bg-[#efe6d8]/45 px-4 py-2 text-center text-xs text-ink/45">
            <span className="inline-flex items-center gap-2">
              <Leaf className="h-3.5 w-3.5 text-moss" />
              {isStreaming ? "Agent 运行中 / 等待人工输入" : "就绪"}
            </span>
          </div>
          <Composer
            value={draft}
            disabled={!canSubmit}
            isStreaming={isStreaming}
            onChange={setDraft}
            onSubmit={() => void startQuery()}
            onStop={() => void stopQuery()}
            toolbar={
              <>
                <AgentPicker
                  agents={agents}
                  value={selectedAgentId}
                  onChange={setSelectedAgentId}
                  disabled={isStreaming}
                />
                <span className="hidden text-xs text-ink/35 sm:inline">
                  自动路由低置信度时会请求确认
                </span>
              </>
            }
          />
        </main>
      </div>
    </div>
  );
}

function applyEvent(message: ChatMessage, event: RunEvent): ChatMessage {
  if (event.event_type === "node.progress") {
    const step = String(event.payload.step ?? "处理中");
    const rawStatus = String(event.payload.status ?? "running");
    const status = rawStatus === "success" || rawStatus === "error" ? rawStatus : "running";
    return {
      ...message,
      status: "streaming",
      content: status === "running" ? `正在执行：${step}` : message.content,
      steps: upsertStep(message.steps, step, status),
    };
  }
  if (event.event_type === "agent.selected") {
    const data = event.payload.data;
    const selected = data && typeof data === "object" ? data as Record<string, unknown> : {};
    return {
      ...message,
      agentId: String(selected.selected_agent_id ?? message.agentId ?? ""),
      steps: upsertStep(message.steps, "选择 Agent", "success"),
    };
  }
  const intervention = asIntervention(event);
  if (intervention) {
    return {
      ...message,
      status: "waiting",
      content:
        intervention.kind === "agent_selection"
          ? "自动路由需要你确认使用哪个 Agent。"
          : "SQL 已生成并通过基础校验，需要人工确认后执行。",
      intervention,
      steps: upsertStep(
        message.steps,
        intervention.kind === "agent_selection" ? "选择 Agent" : "SQL审批",
        "running",
      ),
    };
  }
  if (event.event_type === "agent.result") {
    const output = eventOutput(event);
    return {
      ...message,
      status: event.payload.data && (event.payload.data as AgentOutput).status === "rejected" ? "done" : message.status,
      content: output?.text ?? summarizeResult(output?.rows),
      result: output,
    };
  }
  if (event.event_type === "run.retrying") {
    return { ...message, status: "streaming", content: "依赖暂时不可用，正在从 checkpoint 重试…" };
  }
  if (event.event_type === "run.completed") {
    const output = eventOutput(event);
    return {
      ...message,
      status: "done",
      content: output?.text ?? message.content,
      result: output ?? message.result,
      intervention: message.intervention
        ? { ...message.intervention, status: "responded" }
        : undefined,
    };
  }
  if (event.event_type === "run.rejected") {
    return {
      ...message,
      status: "done",
      content: "SQL 执行已被拒绝。",
      intervention: message.intervention
        ? { ...message.intervention, status: "responded" }
        : undefined,
    };
  }
  if (
    event.event_type === "run.failed" ||
    event.event_type === "run.expired" ||
    event.event_type === "run.cancelled"
  ) {
    return {
      ...message,
      status: event.event_type === "run.cancelled" ? "done" : "error",
      content:
        event.event_type === "run.cancelled"
          ? "已停止本次运行。"
          : "本次运行没有成功。",
      error: String(event.payload.message ?? event.payload.error_code ?? ""),
    };
  }
  return message;
}
