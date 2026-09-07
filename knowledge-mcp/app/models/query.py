from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QueryAnalysis:
    query: str
    subsystem: str | None
    knowledge_types: list[str] = field(default_factory=list)
    identifiers: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
