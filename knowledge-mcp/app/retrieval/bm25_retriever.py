from __future__ import annotations

from collections import Counter
import re

from app.models.document import KnowledgeNode


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_./:-]+", text.lower())


class BM25Retriever:
    """Uses LlamaIndex's BM25 retriever and retains an offline lexical fallback."""

    def __init__(self, nodes: list[KnowledgeNode], top_k: int) -> None:
        self.nodes = {node.node_id: node for node in nodes}
        self.top_k = top_k
        self._retriever = None
        try:
            from llama_index.retrievers.bm25 import BM25Retriever as LlamaBM25Retriever

            self._retriever = LlamaBM25Retriever.from_defaults(
                nodes=[node.llama_node for node in nodes], similarity_top_k=top_k
            )
        except ImportError:
            pass

    def retrieve(self, query: str, allowed_ids: set[str]) -> list[str]:
        if self._retriever is not None:
            return [
                result.node.node_id
                for result in self._retriever.retrieve(query)
                if result.node.node_id in allowed_ids
            ]
        query_terms = Counter(_tokens(query))
        scored = []
        for node in self.nodes.values():
            if node.node_id not in allowed_ids:
                continue
            overlap = sum(min(count, _tokens(node.text).count(term)) for term, count in query_terms.items())
            if overlap:
                scored.append((overlap, node.node_id))
        return [node_id for _, node_id in sorted(scored, reverse=True)[: self.top_k]]
