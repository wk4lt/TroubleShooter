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

const PHASE_LABEL: Record<string, string> = {
  setup: "准备",
  analysis: "分析",
  decision: "决策",
  tool: "执行",
  synthesis: "整理",
};

export function TaskRunCard({ run }: { run: TaskRun }) {
  const toolCalls = run.events.filter((e) => e.type === "tool_call");
  const progressEvents = run.events.filter((e) =>
    e.type === "thinking" || e.type === "tool_call" || e.type === "tool_result"
  );
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
          {progressEvents.length > 0 && (
            <div className="msg-progress">
              {progressEvents.map((event, index) => (
                <div key={`${event.type}-${index}`} className={`progress-${event.type}`}>
                  {event.type === "thinking" && (
                    <>
                      💭 <span className="progress-phase">{PHASE_LABEL[event.phase ?? ""] ?? "过程"}</span>{" "}
                      {event.content}
                    </>
                  )}
                  {event.type === "tool_call" && (
                    <>
                      🔧 <span className="progress-phase">执行</span>{" "}
                      <span className="progress-tool-title">{event.content ?? `调用工具 ${event.tool}`}</span>{" "}
                      <span className="mono">({event.tool})</span>
                      {event.skill && <> · Skill: <span className="mono">{event.skill}</span></>}
                      {event.arguments && (
                        <details className="progress-arguments">
                          <summary>查看参数</summary>
                          <pre>{fmt(event.arguments)}</pre>
                        </details>
                      )}
                    </>
                  )}
                  {event.type === "tool_result" && (
                    <details className="progress-result">
                      <summary>
                        📦 <span className="progress-phase">结果</span>{" "}
                        {event.content ?? `工具 ${event.tool} 已返回结果`}
                        {event.duration_ms != null && <span className="progress-duration"> · {event.duration_ms.toFixed(0)}ms</span>}
                      </summary>
                      <pre>{fmt(event.result)}</pre>
                    </details>
                  )}
                </div>
              ))}
            </div>
          )}

          {running && !hasFinal && progressEvents.length === 0 && (
            <span className="msg-thinking">已发送，等待 Agent 响应…</span>
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
