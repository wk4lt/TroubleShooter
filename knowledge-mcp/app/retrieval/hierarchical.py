from __future__ import annotations

from app.models.document import KnowledgeNode
from app.models.result import RetrievalHit


def merge_parent_context(hits: list[RetrievalHit], nodes: dict[str, KnowledgeNode]) -> list[RetrievalHit]:
    """Promote leaf hits to parent context while preserving the winning score."""
    merged: dict[str, RetrievalHit] = {}
    for hit in hits:
        target = nodes.get(hit.node.parent_id) if hit.node.parent_id else None
        target = target or hit.node
        previous = merged.get(target.node_id)
        candidate = RetrievalHit(target, hit.score, hit.sources)
        if previous is None or candidate.score > previous.score:
            merged[target.node_id] = candidate
    return sorted(merged.values(), key=lambda hit: hit.score, reverse=True)
