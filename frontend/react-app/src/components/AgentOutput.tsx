import { useEffect, useRef } from "react";
import { AgentEvent } from "../types";

interface Props {
  events: AgentEvent[];
}

export function AgentOutput({ events }: Props) {
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (boxRef.current) {
      boxRef.current.scrollTop = boxRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <section className="panel output-panel">
      <h2>Agent Output</h2>
      <div className="output" ref={boxRef}>
        {events.length === 0 && <div className="empty">等待任务...</div>}
        {events.map((e, i) => (
          <div key={i} className={`line line-${e.type}`}>
            {e.type === "tool_call" && (
              <span className="tag tag-tool">🔧 调用工具 {e.tool}</span>
            )}
            {e.type === "tool_result" && (
              <span className="tag tag-result">
                📦 {e.tool}: {stringify(e.result)}
              </span>
            )}
            {e.type === "thinking" && <span className="tag tag-think">💭 {e.content}</span>}
            {e.type === "message" && <span className="text">{e.content}</span>}
            {e.type === "final" && (
              <span className="tag tag-final">✅ 任务完成</span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function stringify(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}
