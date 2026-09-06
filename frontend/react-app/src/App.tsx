import { useCallback, useEffect, useRef, useState } from "react";
import { createTask, setSessionId } from "./api";
import { setLogSessionId, log } from "./logger";
import { AgentEvent, TaskRun } from "./types";
import { TaskCreator } from "./components/TaskCreator";
import { FilePanel } from "./components/FilePanel";
import { SkillsPanel } from "./components/SkillsPanel";
import { TaskRunCard } from "./components/TaskRunCard";
import { ExecutionTimeline } from "./components/ExecutionTimeline";

export default function App() {
  const [runs, setRuns] = useState<TaskRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [sessionId] = useState<string>(() => {
    const id = crypto.randomUUID();
    setSessionId(id);
    setLogSessionId(id);
    return id;
  });
  const sourceRef = useRef<EventSource | null>(null);
  const submittingRef = useRef(false);
  const listRef = useRef<HTMLDivElement>(null);

  const closeStream = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
  }, []);

  useEffect(() => () => closeStream(), [closeStream]);

  const updateRun = useCallback(
    (taskId: string, updater: (r: TaskRun) => TaskRun) => {
      setRuns((prev) =>
        prev.map((r) => (r.taskId === taskId ? updater(r) : r))
      );
    },
    []
  );

  const appendEvent = useCallback((taskId: string, event: AgentEvent) => {
    setRuns((prev) =>
      prev.map((r) =>
        r.taskId === taskId ? { ...r, events: [...r.events, event] } : r
      )
    );
  }, []);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
    if (nearBottom) el.scrollTop = el.scrollHeight;
  }, [runs]);

  const handleSubmit = useCallback(
    async (input: string) => {
      if (submittingRef.current) return;
      submittingRef.current = true;
      closeStream();
      setError(null);

      const pendingId = `pending-${crypto.randomUUID()}`;
      setRuns((prev) => [
        ...prev,
        { taskId: pendingId, input, status: "created", events: [], result: null },
      ]);

      let id: string;
      try {
        id = await createTask(input, selectedSkill);
        log("info", `创建任务 ${id}: ${input}`, { task_id: id });
      } catch (err) {
        submittingRef.current = false;
        const message = err instanceof Error ? err.message : String(err);
        setRuns((prev) =>
          prev.map((r) =>
            r.taskId === pendingId
              ? { ...r, status: "failed", error: message }
              : r
          )
        );
        setError(message);
        log("error", `创建任务失败: ${err}`);
        return;
      }

      setRuns((prev) => [
        ...prev.map((r) =>
          r.taskId === pendingId ? { ...r, taskId: id, status: "running" } : r
        ),
      ]);

      const source = new EventSource(`/api/task/${id}/stream`);
      sourceRef.current = source;
      let streamFinished = false;

      const closeThisStream = () => {
        streamFinished = true;
        source.close();
        if (sourceRef.current === source) sourceRef.current = null;
      };
      submittingRef.current = false;

      const on = (type: AgentEvent["type"], handler: (data: Omit<AgentEvent, "type">) => void) => {
        source.addEventListener(type, (e) =>
          handler(JSON.parse((e as MessageEvent).data))
        );
      };

      on("thinking", (d) => appendEvent(id, { type: "thinking", ...d }));
      on("tool_call", (d) => appendEvent(id, { type: "tool_call", ...d }));
      on("tool_result", (d) => appendEvent(id, { type: "tool_result", ...d }));
      on("message", (d) => appendEvent(id, { type: "message", ...d }));
      on("final", (d) => {
        appendEvent(id, { type: "final", ...d });
        const failed = d.status === "failed";
        updateRun(id, (r) => ({
          ...r,
          result: d.result ?? null,
          status: failed ? "failed" : "completed",
          error: failed ? String(d.result ?? "执行失败") : r.error,
        }));
        log(failed ? "error" : "info", failed ? `任务 ${id} 失败` : `任务 ${id} 完成`, { task_id: id });
        closeThisStream();
      });
      source.onerror = () => {
        if (streamFinished || source.readyState === EventSource.CLOSED) return;
        updateRun(id, (r) => ({
          ...r,
          status: r.status === "running" ? "failed" : r.status,
          error: "连接中断",
        }));
        log("error", `任务 ${id} 流连接中断`, { task_id: id });
        closeThisStream();
      };
    },
    [appendEvent, closeStream, selectedSkill, updateRun]
  );

  const isRunning = runs.some((r) => r.status === "running" || r.status === "created");
  const selectedRun = runs[runs.length - 1] ?? null;

  return (
    <div className="app">
      <header className="header">
        <h1>TroubleShooter</h1>
        <span className="session-id">
          session: <span className="mono">{sessionId.slice(0, 8)}</span>
        </span>
      </header>

      {error && <div className="error">{error}</div>}

      <div className="layout">
        <aside className="sidebar">
          <FilePanel status={isRunning ? "running" : "idle"} />
          <SkillsPanel selected={selectedSkill} onSelect={setSelectedSkill} />
          {selectedRun ? (
            <ExecutionTimeline
              events={selectedRun.events}
              status={selectedRun.status}
            />
          ) : (
            <section className="panel timeline-panel">
              <h2>执行流程</h2>
              <div className="empty">暂无任务</div>
            </section>
          )}
        </aside>

        <main className="main">
          <div className="runs" ref={listRef}>
            {runs.length === 0 && (
              <div className="runs-empty">
                在下方输入任务,每次交互的执行过程都会保留在这里
              </div>
            )}
            {runs.map((run) => (
              <TaskRunCard key={run.taskId} run={run} />
            ))}
          </div>

          <TaskCreator
            onSubmit={handleSubmit}
            disabled={isRunning}
            skill={selectedSkill}
            onClearSkill={() => setSelectedSkill(null)}
          />
        </main>
      </div>
    </div>
  );
}
