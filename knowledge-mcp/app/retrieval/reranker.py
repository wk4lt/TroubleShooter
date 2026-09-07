from __future__ import annotations

from typing import Protocol

from app.models.result import RetrievalHit


class Reranker(Protocol):
    async def rerank(self, query: str, nodes: list[RetrievalHit]) -> list[RetrievalHit]: ...


class NoOpReranker:
    async def rerank(self, query: str, nodes: list[RetrievalHit]) -> list[RetrievalHit]:
        return nodes
