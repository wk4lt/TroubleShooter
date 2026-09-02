let sessionId = "";

export function setLogSessionId(id: string) {
  sessionId = id;
}

type Level = "debug" | "info" | "warning" | "error";

const consoleFn: Record<Level, (...args: unknown[]) => void> = {
  debug: console.debug,
  info: console.info,
  warning: console.warn,
  error: console.error,
};

export function log(level: Level, message: string, extra?: Record<string, unknown>) {
  consoleFn[level](`[frontend] ${message}`);

  const body = {
    level: level.toUpperCase(),
    message,
    source: "frontend",
    session_id: sessionId,
    ...extra,
  };

  try {
    fetch("/api/logs", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Session-Id": sessionId },
      body: JSON.stringify(body),
    }).catch(() => {});
  } catch {
    // 上报失败不影响业务
  }
}
