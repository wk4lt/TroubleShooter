from __future__ import annotations

from app.runtime.knowledge_runtime import KnowledgeRuntime


async def search_runbook(runtime: KnowledgeRuntime, query: str, subsystem: str | None = None, top_k: int = 5) -> dict:
    return await runtime.search_runbook(query, subsystem, top_k)
