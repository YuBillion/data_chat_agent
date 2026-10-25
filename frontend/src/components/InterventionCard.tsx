import { AlertTriangle, Check, Code2, Pencil, ShieldCheck, X } from "lucide-react";
import { useState } from "react";
import { cn } from "../lib/format";
import type { AgentInfo, Intervention } from "../types/agent";

type Decision = {
  action: "select" | "approve" | "edit" | "reject";
  agentId?: string;
  editedSql?: string;
  reason?: string;
};

type Props = {
  intervention: Intervention;
  agents: AgentInfo[];
  disabled?: boolean;
  onRespond: (decision: Decision) => Promise<void>;
};

export function InterventionCard({
  intervention,
  agents,
  disabled,
  onRespond,
}: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editedSql, setEditedSql] = useState(intervention.payload.sql ?? "");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const agentMap = new Map(agents.map((agent) => [agent.agent_id, agent]));

  const respond = async (decision: Decision) => {
    setSubmitting(true);
    setError(null);
    try {
      await onRespond(decision);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setSubmitting(false);
    }
  };

  if (intervention.kind === "agent_selection") {
    return (
      <section className="mt-4 border border-brass/40 bg-brass/10 p-4">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <ShieldCheck className="h-4 w-4 text-brass" />
          请选择本次任务的 Agent
        </div>
        <p className="mt-2 text-sm text-ink/65">
          自动路由置信度不足。请确认要查询真实数据，还是只查看元数据定义。
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {(intervention.payload.candidates ?? []).map((candidate) => {
            const agent = agentMap.get(candidate.agent_id);
            return (
              <button
                key={candidate.agent_id}
                type="button"
                disabled={disabled || submitting}
                onClick={() =>
                  respond({ action: "select", agentId: candidate.agent_id })
                }
                className="border border-ink/15 bg-white/70 px-4 py-3 text-left transition hover:border-moss/40 hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                <div className="text-sm font-semibold">
                  {agent?.display_name ?? candidate.agent_id}
                </div>
                <div className="mt-1 text-xs leading-5 text-ink/55">
                  {agent?.description ?? candidate.reason}
                </div>
              </button>
            );
          })}
        </div>
        {error && <ErrorLine message={error} />}
      </section>
    );
  }

  return (
    <section className="mt-4 border border-tomato/35 bg-tomato/5 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <AlertTriangle className="h-4 w-4 text-tomato" />
          SQL 执行需要人工确认
        </div>
        <span
          className={cn(
            "px-2 py-1 text-[11px] font-semibold uppercase tracking-wider",
            intervention.payload.high_risk
              ? "bg-tomato text-white"
              : "bg-brass/20 text-ink/70",
          )}
        >
          {intervention.payload.high_risk ? "高风险 · 需异人审批" : "普通审批"}
        </span>
      </div>

      <div className="mt-3 grid gap-2 text-xs text-ink/60 sm:grid-cols-3">
        <span>审批轮次：{intervention.payload.round ?? 1}</span>
        <span>估算扫描：{intervention.payload.estimated_rows ?? "未知"} 行</span>
        <span>
          风险：{(intervention.payload.risk_reasons ?? []).join(", ") || "策略要求"}
        </span>
      </div>

      {editing ? (
        <textarea
          value={editedSql}
          onChange={(event) => setEditedSql(event.target.value)}
          rows={8}
          className="mt-3 w-full resize-y border border-ink/15 bg-white/80 p-3 font-mono text-sm leading-6 outline-none focus:border-moss/50"
          aria-label="修改 SQL"
        />
      ) : (
        <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap border border-ink/10 bg-[#272721] p-3 font-mono text-xs leading-6 text-[#f8f1e6]">
          <code>{intervention.payload.sql}</code>
        </pre>
      )}

      <input
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        placeholder="审批意见（拒绝时必填）"
        className="mt-3 w-full border border-ink/15 bg-white/80 px-3 py-2 text-sm outline-none focus:border-moss/50"
      />

      <div className="mt-3 flex flex-wrap gap-2">
        {!editing && (
          <>
            <button
              type="button"
              disabled={disabled || submitting}
              onClick={() => respond({ action: "approve", reason })}
              className="inline-flex items-center gap-2 bg-moss px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              <Check className="h-4 w-4" /> 批准并执行
            </button>
            <button
              type="button"
              disabled={disabled || submitting}
              onClick={() => setEditing(true)}
              className="inline-flex items-center gap-2 border border-ink/15 bg-white/70 px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              <Pencil className="h-4 w-4" /> 修改 SQL
            </button>
          </>
        )}
        {editing && (
          <>
            <button
              type="button"
              disabled={disabled || submitting || !editedSql.trim()}
              onClick={() =>
                respond({
                  action: "edit",
                  editedSql: editedSql.trim(),
                  reason,
                })
              }
              className="inline-flex items-center gap-2 bg-ink px-4 py-2 text-sm font-semibold text-parchment disabled:opacity-50"
            >
              <Code2 className="h-4 w-4" /> 提交修改并重新校验
            </button>
            <button
              type="button"
              onClick={() => {
                setEditing(false);
                setEditedSql(intervention.payload.sql ?? "");
              }}
              className="border border-ink/15 px-4 py-2 text-sm"
            >
              取消修改
            </button>
          </>
        )}
        <button
          type="button"
          disabled={disabled || submitting || !reason.trim()}
          onClick={() => respond({ action: "reject", reason })}
          className="inline-flex items-center gap-2 border border-tomato/35 px-4 py-2 text-sm font-semibold text-tomato disabled:opacity-40"
        >
          <X className="h-4 w-4" /> 拒绝
        </button>
      </div>
      {error && <ErrorLine message={error} />}
    </section>
  );
}

function ErrorLine({ message }: { message: string }) {
  return (
    <div className="mt-3 border border-tomato/30 bg-tomato/10 px-3 py-2 text-sm text-tomato">
      {message}
    </div>
  );
}
