from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from app.config import Settings
from app.ingestion.pipeline import ingest
from app.models.document import KnowledgeDocument, KnowledgeNode
from app.models.result import RetrievalHit
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.exact_retriever import ExactRetriever
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.hierarchical import merge_parent_context
from app.retrieval.reranker import NoOpReranker, Reranker
from app.retrieval.router import KnowledgeBaseRouter
from app.retrieval.vector_retriever import VectorRetriever


class KnowledgeRuntime:
    """Owns ingestion and retrieval; MCP tools only call this boundary."""

    def __init__(self, settings: Settings, reranker: Reranker | None = None) -> None:
        self.settings = settings
        self.reranker = reranker or NoOpReranker()
        self.documents: list[KnowledgeDocument] = []
        self.nodes: dict[str, KnowledgeNode] = {}
        self.retrieval_node_ids: set[str] = set()
        self.nodes_by_document: dict[str, list[KnowledgeNode]] = defaultdict(list)
        self.router: KnowledgeBaseRouter | None = None
        self.vector: VectorRetriever | None = None
        self.bm25: BM25Retriever | None = None
        self.exact: ExactRetriever | None = None

    def rebuild(self) -> dict[str, int]:
        hierarchy = self.settings.retrieval["hierarchy"]
        result = ingest(
            str(self.settings.knowledge_dir),
            [int(size) for size in hierarchy["chunk_sizes"]],
            bool(hierarchy["enabled"]),
        )
        self.documents = result.documents
        self.nodes = {node.node_id: node for node in result.nodes}
        parent_ids = {node.parent_id for node in result.nodes if node.parent_id}
        retrieval_nodes = [node for node in result.nodes if node.node_id not in parent_ids]
        self.retrieval_node_ids = {node.node_id for node in retrieval_nodes}
        self.nodes_by_document = defaultdict(list)
        for node in result.nodes:
            self.nodes_by_document[node.doc_id].append(node)
        self.router = KnowledgeBaseRouter(self.documents)
        retrieval = self.settings.retrieval
        if retrieval["vector"]["enabled"] and retrieval_nodes:
            self.vector = VectorRetriever(
                retrieval_nodes, self.settings.values["embedding"], int(retrieval["vector"]["top_k"])
            )
        else:
            self.vector = None
        self.bm25 = (
            BM25Retriever(retrieval_nodes, int(retrieval["bm25"]["top_k"]))
            if retrieval["bm25"]["enabled"] and retrieval_nodes else None
        )
        self.exact = ExactRetriever(retrieval_nodes) if retrieval["exact"]["enabled"] else None
        return {"documents": len(self.documents), "nodes": len(self.nodes)}

    def _ensure_ready(self) -> None:
        if self.router is None:
            self.rebuild()

    async def search(
        self,
        query: str,
        subsystem: str | None = None,
        knowledge_types: list[str] | None = None,
        top_k: int = 8,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        self._ensure_ready()
        assert self.router is not None
        analysis_started = time.perf_counter()
        analysis = self.router.analyze(query, subsystem, knowledge_types)
        allowed_nodes = {
            node_id for node_id, node in self.nodes.items()
            if node_id in self.retrieval_node_ids and self.router.matches(node.metadata, analysis)
        }
        router_ms = round((time.perf_counter() - analysis_started) * 1000, 2)
        vector_started = time.perf_counter()
        vector_ids = self.vector.retrieve(query, allowed_nodes) if self.vector else []
        vector_ms = round((time.perf_counter() - vector_started) * 1000, 2)
        bm25_started = time.perf_counter()
        bm25_ids = self.bm25.retrieve(query, allowed_nodes) if self.bm25 else []
        bm25_ms = round((time.perf_counter() - bm25_started) * 1000, 2)
        exact_ids = self.exact.retrieve(analysis.identifiers, allowed_nodes) if self.exact else []
        fusion_started = time.perf_counter()
        retrieval = self.settings.retrieval
        fused = reciprocal_rank_fusion(
            {"vector": vector_ids, "bm25": bm25_ids},
            int(retrieval["fusion"]["k"]), int(retrieval["fusion"]["top_k"]),
        )
        exact_set = set(exact_ids)
        boost = float(retrieval["exact"]["boost"])
        hits = [
            RetrievalHit(self.nodes[node_id], score + (boost if node_id in exact_set else 0), sources)
            for node_id, score, sources in fused
        ]
        fusion_ms = round((time.perf_counter() - fusion_started) * 1000, 2)
        rerank_started = time.perf_counter()
        reranked = await self.reranker.rerank(query, hits)
        reranked = reranked[: int(retrieval["rerank"]["top_k"])]
        if retrieval["hierarchy"]["enabled"]:
            reranked = merge_parent_context(reranked, self.nodes)
        final_hits = reranked[:max(1, min(top_k, 20))]
        rerank_ms = round((time.perf_counter() - rerank_started) * 1000, 2)
        total_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "query": query,
            "router": {
                "subsystem": analysis.subsystem,
                "knowledge_types": analysis.knowledge_types,
                "selected": self.router.selected_bases(analysis, self.documents),
            },
            "results": [hit.to_dict() for hit in final_hits],
            "trace": {
                "query_analysis": {
                    "subsystem": analysis.subsystem,
                    "identifiers": analysis.identifiers,
                    "keywords": analysis.keywords,
                },
                "router": {"selected": self.router.selected_bases(analysis, self.documents)},
                "vector_hits": len(vector_ids),
                "bm25_hits": len(bm25_ids),
                "exact_hits": len(exact_ids),
                "fusion_hits": len(fused),
                "rerank_hits": len(reranked),
                "final_results": len(final_hits),
                "latency_ms": {
                    "router": router_ms, "vector": vector_ms, "bm25": bm25_ms,
                    "fusion": fusion_ms, "reranker": rerank_ms, "total": total_ms,
                },
            },
        }

    async def search_runbook(self, query: str, subsystem: str | None = None, top_k: int = 5) -> dict[str, Any]:
        payload = await self.search(query, subsystem, ["runbook"], top_k)
        results = []
        for result in payload["results"]:
            document = self.get_document(result["doc_id"])
            text = document["text"] if document else result["text"]
            sections = _runbook_sections(text)
            results.append({
                "runbook_id": result["doc_id"], "title": result["title"], "score": result["score"],
                "trigger": sections.get("trigger", ""), "procedure": sections.get("procedure", ""),
                "decision": sections.get("decision", ""), "escalation": sections.get("escalation", ""),
                "source_path": result["source_path"],
            })
        return {"query": query, "results": results, "trace": payload["trace"]}

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        documents = [document for document in self.documents if document.doc_id == doc_id]
        if not documents:
            return None
        document = documents[0]
        return {"doc_id": document.doc_id, "title": document.title, "text": document.text, "metadata": document.metadata}

    def get_context(self, node_id: str, direction: str = "parent") -> dict[str, Any] | None:
        node = self.nodes.get(node_id)
        if node is None:
            return None
        target = self.nodes.get(node.parent_id) if direction == "parent" and node.parent_id else node
        if target is None:
            target = node
        return {"node_id": target.node_id, "doc_id": target.doc_id, "text": target.text, "metadata": target.metadata}

    def list_knowledge_bases(self) -> dict[str, Any]:
        self._ensure_ready()
        grouped: dict[str, set[str]] = defaultdict(set)
        for document in self.documents:
            grouped[str(document.metadata["subsystem"])].add(str(document.metadata["knowledge_type"]))
        return {"knowledge_bases": [
            {"subsystem": subsystem, "types": sorted(types)} for subsystem, types in sorted(grouped.items())
        ]}


def _runbook_sections(text: str) -> dict[str, str]:
    names = {
        "trigger": "trigger",
        "symptoms": "symptoms",
        "procedure": "procedure",
        "immediate steps": "procedure",
        "immediate mitigation": "procedure",
        "auto-remediation steps": "procedure",
        "decision": "decision",
        "decision tree": "decision",
        "escalation": "escalation",
    }
    sections: dict[str, list[str]] = defaultdict(list)
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("#"):
            name = line.lstrip("#").strip().lower()
            current = names.get(name)
        elif current:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}
