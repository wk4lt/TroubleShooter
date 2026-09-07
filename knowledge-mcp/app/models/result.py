from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .document import KnowledgeNode


@dataclass(frozen=True)
class RetrievalHit:
    node: KnowledgeNode
    score: float
    sources: list[str]

    def to_dict(self) -> dict[str, Any]:
        metadata = self.node.metadata
        return {
            "doc_id": self.node.doc_id,
            "node_id": self.node.node_id,
            "title": metadata["title"],
            "text": self.node.text,
            "score": round(self.score, 4),
            "subsystem": metadata["subsystem"],
            "knowledge_type": metadata["knowledge_type"],
            "source_path": metadata["source_path"],
        }
