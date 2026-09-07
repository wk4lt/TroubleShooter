from __future__ import annotations

from app.runtime.knowledge_runtime import KnowledgeRuntime


async def search_knowledge(runtime: KnowledgeRuntime, query: str, subsystem: str | None = None,
                           knowledge_types: list[str] | None = None, top_k: int = 8) -> dict:
    return await runtime.search(query, subsystem, knowledge_types, top_k)
