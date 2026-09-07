from __future__ import annotations

import re

from app.models.document import KnowledgeDocument
from app.models.query import QueryAnalysis


IDENTIFIER_RE = re.compile(r"\b[A-Z][A-Z0-9_]{1,}(?:-\d+[A-Z0-9_-]*)+\b", re.IGNORECASE)
TYPE_WORDS = {
    "runbook": (
        "runbook", "sop", "procedure", "incident", "playbook", "排障", "处置",
        "error rate", "after deployment", "5xx", "failed", "failure", "outage",
    ),
    "issue": ("issue", "bug", "defect", "问题"),
    "design_doc": ("design", "architecture", "设计"),
    "reference": ("reference", "manual", "文档"),
}


class KnowledgeBaseRouter:
    def __init__(self, documents: list[KnowledgeDocument]) -> None:
        self.subsystems = {document.metadata["subsystem"] for document in documents}

    def analyze(
        self, query: str, subsystem: str | None = None, knowledge_types: list[str] | None = None
    ) -> QueryAnalysis:
        normalized = query.lower()
        selected = subsystem.upper() if subsystem else None
        if not selected:
            for candidate in sorted(self.subsystems, key=len, reverse=True):
                if candidate != "COMMON" and re.search(rf"\b{re.escape(candidate.lower())}\b", normalized):
                    selected = candidate
                    break
        selected_types = list(knowledge_types or [])
        if not selected_types:
            selected_types = [
                name for name, words in TYPE_WORDS.items() if any(word in normalized for word in words)
            ]
        identifiers = [value.upper() for value in IDENTIFIER_RE.findall(query)]
        keywords = re.findall(r"[a-zA-Z][a-zA-Z0-9_]+", normalized)
        return QueryAnalysis(query, selected, selected_types, identifiers, keywords)

    @staticmethod
    def matches(node_metadata: dict[str, object], analysis: QueryAnalysis) -> bool:
        subsystem = str(node_metadata["subsystem"])
        if analysis.subsystem and subsystem not in {analysis.subsystem, "COMMON"}:
            return False
        selected_types = analysis.knowledge_types
        return not selected_types or str(node_metadata["knowledge_type"]) in selected_types

    def selected_bases(self, analysis: QueryAnalysis, documents: list[KnowledgeDocument]) -> list[str]:
        bases = {
            f"{document.metadata['subsystem']}/{document.metadata['knowledge_type']}"
            for document in documents
            if self.matches(document.metadata, analysis)
        }
        return sorted(bases)
