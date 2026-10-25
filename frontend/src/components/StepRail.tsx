import { Check, Circle, LoaderCircle, X } from "lucide-react";
import { cn } from "../lib/format";
import type { ProgressStatus, StepState } from "../types/agent";

function NodeIcon({ status }: { status: ProgressStatus }) {
  if (status === "running") {
    return <LoaderCircle className="h-3.5 w-3.5 animate-spin" />;
  }
  if (status === "success") return <Check className="h-3.5 w-3.5" />;
  if (status === "error") return <X className="h-3.5 w-3.5" />;
  return <Circle className="h-3.5 w-3.5" />;
}

export function StepRail({ steps = [] }: { steps?: StepState[] }) {
  if (steps.length === 0) return null;

  return (
    <section className="mt-4 border border-ink/10 bg-white/40 p-4 shadow-line">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-sm font-semibold text-ink">Agent 执行轨迹</div>
        <div className="text-xs text-ink/45">LangGraph</div>
      </div>
      <ol className="grid gap-2 sm:grid-cols-2">
        {steps.map((step, index) => (
          <li
            key={`${step.step}-${index}`}
            className={cn(
              "flex items-center gap-3 border px-3 py-2 text-sm",
              step.status === "running" && "border-brass/40 bg-brass/10",
              step.status === "success" && "border-moss/20 bg-moss/10",
              step.status === "error" && "border-tomato/30 bg-tomato/10",
            )}
          >
            <span
              className={cn(
                "grid h-6 w-6 shrink-0 place-items-center rounded-full",
                step.status === "running" && "bg-brass/20 text-brass",
                step.status === "success" && "bg-moss/15 text-moss",
                step.status === "error" && "bg-tomato/15 text-tomato",
              )}
            >
              <NodeIcon status={step.status} />
            </span>
            <span className="min-w-0 flex-1 truncate">{step.step}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
