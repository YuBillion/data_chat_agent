import { Bot } from "lucide-react";
import type { AgentInfo } from "../types/agent";

export function AgentPicker({
  agents,
  value,
  onChange,
  disabled,
}: {
  agents: AgentInfo[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="inline-flex items-center gap-2 text-xs text-ink/55">
      <Bot className="h-3.5 w-3.5" aria-hidden="true" />
      <span className="sr-only">选择 Agent</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="max-w-44 border border-ink/10 bg-white/60 px-2 py-1 text-xs text-ink outline-none focus:border-moss/45 disabled:opacity-50"
      >
        <option value="">自动路由</option>
        {agents.map((agent) => (
          <option key={agent.agent_id} value={agent.agent_id}>
            {agent.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}
