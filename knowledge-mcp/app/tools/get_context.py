from __future__ import annotations

from app.runtime.knowledge_runtime import KnowledgeRuntime


def get_context(runtime: KnowledgeRuntime, node_id: str, direction: str = "parent") -> dict:
    return runtime.get_context(node_id, direction) or {"error": f"node not found: {node_id}"}
