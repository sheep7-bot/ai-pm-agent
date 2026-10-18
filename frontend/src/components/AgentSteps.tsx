import { useState } from "react";
import type { StepEvent } from "../types";

const NODE_LABEL: Record<string, string> = {
  analyze: "需求分析",
  planning: "任务规划",
  research: "工具调用",
  draft_prd: "PRD 生成",
  revise_prd: "PRD 修订",
};

interface Props {
  events: StepEvent[];
  running?: boolean;
}

export default function AgentSteps({ events, running }: Props) {
  const [open, setOpen] = useState(true);

  if (events.length === 0 && !running) return null;

  const toolCount = events.filter((e) => e.node === "research").length;

  return (
    <div className={"steps" + (running ? " running" : "")}>
      <button className="steps-head" onClick={() => setOpen((v) => !v)}>
        <span className="steps-icon">{running ? "◍" : "✓"}</span>
        <span className="steps-label">{running ? "执行中" : "执行过程"}</span>
        <span className="steps-meta">
          {events.length} 步{toolCount > 0 ? ` · ${toolCount} 次工具调用` : ""}
        </span>
        <span className={"steps-caret" + (open ? " open" : "")}>▾</span>
      </button>

      {open && (
        <ol className="steps-list">
          {events.map((e, i) => (
            <li className="astep" key={i} style={{ animationDelay: `${Math.min(i, 8) * 45}ms` }}>
              <span className="astep-line" aria-hidden />
              <span className="astep-dot" data-status={e.status} />
              <div className="astep-body">
                <div className="astep-head">
                  <span className="astep-node">{NODE_LABEL[e.node] || e.node}</span>
                  <span className="astep-title">{e.title}</span>
                </div>
                {e.detail && <div className="astep-detail">{e.detail}</div>}
              </div>
            </li>
          ))}
          {running && (
            <li className="astep pending">
              <span className="astep-line" aria-hidden />
              <span className="astep-dot" data-status="running" />
              <div className="astep-body">
                <div className="astep-head">
                  <span className="astep-title dim">
                    <i /> <i /> <i /> 处理中
                  </span>
                </div>
              </div>
            </li>
          )}
        </ol>
      )}
    </div>
  );
}
