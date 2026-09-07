from __future__ import annotations

import re
from typing import Any

from llama_index.core import Document
from llama_index.core.node_parser import HierarchicalNodeParser, SentenceSplitter

from app.models.document import KnowledgeDocument, KnowledgeNode


def _offline_sentence_tokenizer(text: str) -> list[str]:
    """Avoid LlamaIndex's optional NLTK data download during local ingestion."""
    return re.findall(r"[^,.;。？！\n]+[,.;。？！]?", text)


def build_hierarchical_nodes(
    documents: list[KnowledgeDocument], chunk_sizes: list[int], enabled: bool = True
) -> list[KnowledgeNode]:
    """Delegate node splitting and parent relationships to LlamaIndex."""
    llama_documents = [
        Document(text=document.text, id_=document.doc_id, metadata=document.metadata)
        for document in documents
    ]
    if enabled:
        parser_ids = [f"level_{size}" for size in chunk_sizes]
        parser = HierarchicalNodeParser.from_defaults(
            node_parser_ids=parser_ids,
            node_parser_map={
                parser_id: SentenceSplitter(
                    chunk_size=size, chunk_overlap=min(32, size // 8),
                    chunking_tokenizer_fn=_offline_sentence_tokenizer,
                )
                for parser_id, size in zip(parser_ids, chunk_sizes)
            },
        )
        raw_nodes = parser.get_nodes_from_documents(llama_documents)
    else:
        parser = SentenceSplitter(
            chunk_size=chunk_sizes[-1], chunk_overlap=32,
            chunking_tokenizer_fn=_offline_sentence_tokenizer,
        )
        raw_nodes = parser.get_nodes_from_documents(llama_documents)

    nodes: list[KnowledgeNode] = []
    for raw_node in raw_nodes:
        metadata: dict[str, Any] = dict(raw_node.metadata)
        parent = raw_node.parent_node
        nodes.append(
            KnowledgeNode(
                node_id=raw_node.node_id,
                doc_id=str(metadata["doc_id"]),
                text=raw_node.get_content(),
                metadata=metadata,
                parent_id=parent.node_id if parent is not None else None,
                level=0 if parent is None else 1,
                llama_node=raw_node,
            )
        )
    return nodes
