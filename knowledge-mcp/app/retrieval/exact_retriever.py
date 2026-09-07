from __future__ import annotations

from app.models.document import KnowledgeNode


class ExactRetriever:
    def __init__(self, nodes: list[KnowledgeNode]) -> None:
        self.nodes = nodes

    def retrieve(self, identifiers: list[str], allowed_ids: set[str]) -> list[str]:
        if not identifiers:
            return []
        hits = []
        for node in self.nodes:
            if node.node_id not in allowed_ids:
                continue
            corpus = " ".join((node.text, node.metadata["title"], " ".join(node.metadata["tags"]))).upper()
            if any(identifier in corpus for identifier in identifiers):
                hits.append(node.node_id)
        return hits
