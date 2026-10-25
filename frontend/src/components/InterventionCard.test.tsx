import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { InterventionCard } from "./InterventionCard";
import type { AgentInfo, Intervention } from "../types/agent";

const agents: AgentInfo[] = [
  {
    agent_id: "analytics_sql",
    version: "1.0.0",
    display_name: "问数 Agent",
    description: "查询真实业务数据",
    capabilities: [],
    response_types: [],
  },
  {
    agent_id: "catalog_qa",
    version: "1.0.0",
    display_name: "元数据问答 Agent",
    description: "解释元数据定义",
    capabilities: [],
    response_types: [],
  },
];

function intervention(overrides: Partial<Intervention>): Intervention {
  return {
    id: "intervention-1",
    run_id: "run-1",
    kind: "agent_selection",
    status: "pending",
    payload: {
      candidates: [
        {
          agent_id: "analytics_sql",
          confidence: 0.5,
          reason: "data query",
        },
        {
          agent_id: "catalog_qa",
          confidence: 0.48,
          reason: "definition",
        },
      ],
    },
    version: 1,
    requested_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 60_000).toISOString(),
    decision: null,
    actor_id: null,
    responded_at: null,
    ...overrides,
  };
}

describe("InterventionCard", () => {
  it("submits an explicit Agent selection", async () => {
    const onRespond = vi.fn().mockResolvedValue(undefined);
    render(
      <InterventionCard
        intervention={intervention({})}
        agents={agents}
        onRespond={onRespond}
      />,
    );

    fireEvent.click(screen.getByText("元数据问答 Agent"));
    await waitFor(() =>
      expect(onRespond).toHaveBeenCalledWith({
        action: "select",
        agentId: "catalog_qa",
      }),
    );
  });

  it("requires a reason before rejecting SQL", async () => {
    const onRespond = vi.fn().mockResolvedValue(undefined);
    render(
      <InterventionCard
        intervention={intervention({
          kind: "sql_approval",
          payload: {
            sql: "SELECT region_name FROM dim_region",
            sql_hash: "a".repeat(64),
            high_risk: false,
            round: 1,
            risk_reasons: ["corrected_sql"],
          },
        })}
        agents={agents}
        onRespond={onRespond}
      />,
    );

    const reject = screen.getByRole("button", { name: "拒绝" });
    expect(reject).toBeDisabled();
    fireEvent.change(screen.getByPlaceholderText("审批意见（拒绝时必填）"), {
      target: { value: "口径不符合要求" },
    });
    fireEvent.click(reject);
    await waitFor(() =>
      expect(onRespond).toHaveBeenCalledWith({
        action: "reject",
        reason: "口径不符合要求",
      }),
    );
  });

  it("submits edited SQL", async () => {
    const onRespond = vi.fn().mockResolvedValue(undefined);
    render(
      <InterventionCard
        intervention={intervention({
          kind: "sql_approval",
          payload: {
            sql: "SELECT 1",
            sql_hash: "b".repeat(64),
            high_risk: false,
            round: 1,
            risk_reasons: ["corrected_sql"],
          },
        })}
        agents={agents}
        onRespond={onRespond}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /修改 SQL/ }));
    fireEvent.change(screen.getByLabelText("修改 SQL"), {
      target: { value: "SELECT 2" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /提交修改并重新校验/ }),
    );
    await waitFor(() =>
      expect(onRespond).toHaveBeenCalledWith({
        action: "edit",
        editedSql: "SELECT 2",
        reason: "",
      }),
    );
  });
});
