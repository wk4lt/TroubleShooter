from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class KnowledgeDocument:
    doc_id: str
    title: str
    text: str
    source_path: str
    metadata: dict[str, Any]
    path: Path


@dataclass(frozen=True)
class KnowledgeNode:
    node_id: str
    doc_id: str
    text: str
    metadata: dict[str, Any]
    parent_id: str | None = None
    level: int = 0
    llama_node: Any = field(default=None, compare=False, repr=False)
