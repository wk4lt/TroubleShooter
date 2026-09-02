import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from app.storage.logs import log_store

_STRUCTURED_FIELDS = ("session_id", "task_id", "tool")

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


class MemoryHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "ts": record.created,
                "level": record.levelname,
                "source": getattr(record, "source", "backend"),
                "message": record.getMessage(),
            }
            for key in _STRUCTURED_FIELDS:
                value = getattr(record, key, None)
                if value:
                    entry[key] = value
            if record.exc_info:
                entry["exception"] = self.format(record)
            log_store.add(entry)
        except Exception:  # noqa: BLE001
            self.handleError(record)


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if any(isinstance(h, MemoryHandler) for h in root.handlers):
        return

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    root.addHandler(MemoryHandler())


def log_event(
    message: str, level: str = "info", source: str = "backend", **fields: Any
) -> None:
    logger = logging.getLogger("app")
    method = getattr(logger, level.lower(), logger.info)
    method(message, extra={"source": source, **fields})
