import { AgentEvent } from "../types";

interface Props {
  events: AgentEvent[];
  status: string;
}

interface Step {
  label: string;
  state: "done" | "active" | "waiting";
}

export function ExecutionTimeline({ events, status }: Props) {
  const steps: Step[] = [{ label: "Task Created", state: "done" }];

  const hasThinking = events.some((e) => e.type === "thinking");
  if (hasThinking || status === "running") {
    steps.push({ label: "Agent Started", state: "done" });
  }

  for (const e of events) {
    if (e.type === "tool_call") {
      steps.push({ label: `Calling Tool: ${e.tool}`, state: "done" });
    } else if (e.type === "tool_result") {
      steps.push({ label: `Tool Result: ${e.tool}`, state: "done" });
    }
  }

  const hasFinal = events.some((e) => e.type === "final");
  if (hasFinal) {
    steps.push({ label: "Task Finished", state: "done" });
  } else if (status === "running") {
    steps.push({ label: "Waiting", state: "active" });
  }

  return (
    <section className="panel timeline-panel">
      <h2>执行流程</h2>
      <ul className="timeline">
        {steps.map((s, i) => (
          <li key={i} className={`step step-${s.state}`}>
            <span className="mark">
              {s.state === "done" ? "✓" : s.state === "active" ? "●" : "○"}
            </span>
            <span className="label">{s.label}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
