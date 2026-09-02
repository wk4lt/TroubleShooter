import contextvars

current_session_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_session_id", default=""
)
