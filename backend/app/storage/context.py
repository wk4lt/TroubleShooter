import contextvars

current_session_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_session_id", default=""
)
current_skill: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_skill", default=""
)
current_task_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_task_id", default=""
)
current_workspace_dir: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_workspace_dir", default=""
)
