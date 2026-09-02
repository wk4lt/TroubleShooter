import { TaskRun } from "../types";

const STATUS_LABEL: Record<string, string> = {
  created: "已创建",
  running: "执行中",
  completed: "已完成",
  failed: "失败",
};

function fmt(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}

export function TaskRunCard({ run }: { run: TaskRun }) {
  const toolCalls = run.events.filter((e) => e.type === "tool_call");
  const messages = run.events
    .filter((e) => e.type === "message")
    .map((e) => e.content)
    .filter(Boolean)
    .join("\n");
  const hasFinal = run.events.some((e) => e.type === "final");
  const running = run.status === "running" || run.status === "created";

  return (
    <div className="turn">
      <div className="msg msg-user">
        <div className="msg-body">{run.input}</div>
      </div>

      <div className="msg msg-agent">
        <div className="msg-role">
          Agent
          <span className={`msg-status status-${run.status}`}>
            {STATUS_LABEL[run.status] ?? run.status}
          </span>
        </div>
        <div className="msg-body">
          {running && !hasFinal && (
            <span className="msg-thinking">正在处理…</span>
          )}

          {messages ? (
            <div className="msg-text">{messages}</div>
          ) : (
            run.status === "completed" && run.result != null && (
              <pre className="msg-result">{fmt(run.result)}</pre>
            )
          )}

          {toolCalls.length > 0 && (
            <details className="msg-tools">
              <summary>🔧 {toolCalls.length} 次工具调用</summary>
              <ul>
                {toolCalls.map((t, i) => (
                  <li key={i}>
                    <span className="mono">{t.tool}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}

          {run.error && <div className="msg-error">{run.error}</div>}
        </div>
      </div>
    </div>
  );
}
