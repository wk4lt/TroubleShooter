from __future__ import annotations

from app.runtime.knowledge_runtime import KnowledgeRuntime


def get_document(runtime: KnowledgeRuntime, doc_id: str) -> dict:
    return runtime.get_document(doc_id) or {"error": f"document not found: {doc_id}"}
