from __future__ import annotations

from app.runtime.knowledge_runtime import KnowledgeRuntime


def list_knowledge_bases(runtime: KnowledgeRuntime) -> dict:
    return runtime.list_knowledge_bases()
