import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.files import router as files_router
from app.api.logs import router as logs_router
from app.api.knowledge import router as knowledge_router
from app.api.skills import router as skills_router
from app.api.task import router as task_router
from app.api.stream import router as stream_router
from app.config import settings
from app.logger import log_event, setup_logging
from app.storage.sessions import sessions

setup_logging()


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(60)
        try:
            count = sessions.cleanup_expired(settings.session_ttl_seconds)
            if count:
                log_event(
                    f"清理 {count} 个过期 session 及其文件",
                    level="info",
                    source="system",
                )
        except Exception as exc:  # noqa: BLE001
            log_event(f"session 清理异常: {exc}", level="error", source="system")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_cleanup_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="TroubleShooter", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    path = request.url.path
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    if not path.startswith("/api/logs") and path != "/health":
        log_event(
            f"{request.method} {path} -> {response.status_code} ({duration:.0f}ms)",
            level="info",
            source="http",
        )
    return response


app.include_router(task_router)
app.include_router(stream_router)
app.include_router(files_router)
app.include_router(logs_router)
app.include_router(knowledge_router)
app.include_router(skills_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
