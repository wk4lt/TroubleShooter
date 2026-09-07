from __future__ import annotations

from typing import Any

from llama_index.core import VectorStoreIndex
from llama_index.core.embeddings.mock_embed_model import MockEmbedding

from app.models.document import KnowledgeNode


class VectorRetriever:
    """LlamaIndex VectorIndexRetriever behind a replaceable embedding provider."""

    def __init__(self, nodes: list[KnowledgeNode], embedding: dict[str, Any], top_k: int) -> None:
        self.nodes = {node.node_id: node for node in nodes}
        provider = str(embedding.get("provider", "mock"))
        self._mock = provider == "mock"
        if provider == "huggingface":
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding

            embed_model = HuggingFaceEmbedding(model_name=str(embedding["model"]))
        elif provider == "mock":
            embed_model = MockEmbedding(embed_dim=int(embedding.get("dimension", 384)))
        else:
            raise ValueError(f"unsupported embedding provider: {provider}")
        self.index = VectorStoreIndex(
            [node.llama_node for node in nodes], embed_model=embed_model, show_progress=False
        )
        self.retriever = self.index.as_retriever(similarity_top_k=top_k)

    def retrieve(self, query: str, allowed_ids: set[str]) -> list[str]:
        # MockEmbedding exists to verify the LlamaIndex VectorStore lifecycle
        # offline, but it gives every text the same vector and must not inject
        # arbitrary ordering into RRF. Use a configured real provider for
        # semantic vector retrieval.
        if self._mock:
            return []
        return [
            result.node.node_id
            for result in self.retriever.retrieve(query)
            if result.node.node_id in allowed_ids
        ]
