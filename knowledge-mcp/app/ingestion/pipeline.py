from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.hierarchical_parser import build_hierarchical_nodes
from app.ingestion.loader import load_documents
from app.models.document import KnowledgeDocument, KnowledgeNode


@dataclass(frozen=True)
class IngestionResult:
    documents: list[KnowledgeDocument]
    nodes: list[KnowledgeNode]


def ingest(knowledge_dir: str, chunk_sizes: list[int], hierarchy_enabled: bool = True) -> IngestionResult:
    from pathlib import Path

    documents = load_documents(Path(knowledge_dir))
    return IngestionResult(
        documents=documents,
        nodes=build_hierarchical_nodes(documents, chunk_sizes, hierarchy_enabled),
    )
