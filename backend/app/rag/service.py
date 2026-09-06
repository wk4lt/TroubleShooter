import hashlib
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from llama_index.core import Document
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter

from app.config import settings
from app.logger import log_event


TEXT_EXTENSIONS = {
    ".md", ".markdown", ".txt", ".rst", ".json", ".yaml", ".yml", ".csv",
    ".xml", ".html", ".htm", ".py", ".js", ".ts", ".tsx", ".java", ".go",
    ".sql", ".log", ".pdf",
}
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def _terms(text: str) -> List[str]:
    """Create useful tokens for both Chinese text and technical identifiers."""
    normalized = text.lower()
    words = re.findall(r"[a-z0-9_./:-]+", normalized)
    cjk = re.findall(r"[\u3400-\u9fff]", normalized)
    bigrams = ["".join(cjk[i : i + 2]) for i in range(len(cjk) - 1)]
    return words + cjk + bigrams


def _chunking_tokenizer(text: str) -> List[str]:
    """Avoid LlamaIndex's optional NLTK download in an isolated deployment."""
    return re.findall(r"[^,.;。？！\n]+[,.;。？！]?", text)


class KnowledgeService:
    """Process-local RAG index for the first usable version.

    LlamaIndex owns Document/node creation and hierarchical chunking. Retrieval
    uses a dependency-free lexical scorer for now, so the service works in an
    isolated network without downloading an embedding model. The node contract
    is intentionally compatible with adding vector/hybrid retrieval later.
    """

    def __init__(self) -> None:
        self.root = Path(settings.rag_knowledge_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._nodes_by_path: Dict[str, List[Dict[str, Any]]] = {}
        self._fingerprints: Dict[str, str] = {}
        self._ready = False

    @staticmethod
    def _read(path: Path) -> Optional[str]:
        if not path.is_file() or path.stat().st_size > MAX_DOCUMENT_BYTES:
            return None
        if path.suffix.lower() == ".pdf":
            try:
                from PyPDF2 import PdfReader

                return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
            except Exception as exc:  # noqa: BLE001
                log_event(f"RAG PDF 解析失败 {path.name}: {exc}", level="warning", source="rag")
                return None
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            return None
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    @staticmethod
    def _fingerprint(path: Path) -> str:
        stat = path.stat()
        return f"{stat.st_mtime_ns}:{stat.st_size}"

    def _metadata(self, path: Path, base: Path, source_kind: str) -> Dict[str, Any]:
        relative = path.relative_to(base).as_posix()
        parts = relative.split("/")
        if source_kind == "knowledge" and len(parts) >= 3:
            subsystem_id, knowledge_type = parts[0], parts[1]
            source = "/".join(parts)
        else:
            subsystem_id, knowledge_type, source = "session", "workspace", relative
        return {
            "source": source,
            "source_kind": source_kind,
            "file_path": str(path),
            "filename": path.name,
            "subsystem_id": subsystem_id,
            "knowledge_type": knowledge_type,
        }

    def _build_nodes(self, path: Path, base: Path, source_kind: str) -> List[Dict[str, Any]]:
        content = self._read(path)
        if not content or not content.strip():
            return []
        metadata = self._metadata(path, base, source_kind)
        document = Document(text=content, metadata=metadata, doc_id=metadata["source"])
        pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(
                    chunk_size=settings.rag_chunk_size,
                    chunk_overlap=settings.rag_chunk_overlap,
                    chunking_tokenizer_fn=_chunking_tokenizer,
                )
            ]
        )
        nodes = pipeline.run(documents=[document])
        result: List[Dict[str, Any]] = []
        for index, node in enumerate(nodes):
            text = node.get_content()
            node_metadata = dict(metadata)
            node_metadata["chunk_index"] = index
            result.append({
                "id": hashlib.sha1(
                    (metadata["source"] + ":" + str(index)).encode()
                ).hexdigest()[:16],
                "text": text,
                "metadata": node_metadata,
                "terms": _terms(text),
            })
        return result

    def _iter_files(self, base: Path) -> Iterable[Path]:
        if not base.exists():
            return []
        return (
            path for path in base.rglob("*")
            if path.is_file()
            and not any(part.startswith(".") for part in path.relative_to(base).parts)
        )

    def refresh(self) -> Dict[str, int]:
        """Incrementally index files under backend/data/knowledge."""
        with self._lock:
            current: Dict[str, str] = {}
            for path in self._iter_files(self.root):
                key = str(path)
                try:
                    fingerprint = self._fingerprint(path)
                except OSError:
                    continue
                current[key] = fingerprint
                if self._fingerprints.get(key) != fingerprint:
                    self._nodes_by_path[key] = self._build_nodes(path, self.root, "knowledge")
            for key in set(self._nodes_by_path) - set(current):
                self._nodes_by_path.pop(key, None)
            self._fingerprints = current
            self._ready = True
            documents = len(self._nodes_by_path)
            chunks = sum(len(nodes) for nodes in self._nodes_by_path.values())
            log_event(
                f"RAG 索引刷新 documents={documents} chunks={chunks}",
                source="rag",
            )
            return {"documents": documents, "chunks": chunks}

    def search(
        self,
        query: str,
        top_k: int = 5,
        subsystem_id: Optional[str] = None,
        knowledge_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        started_at = time.perf_counter()
        if not query.strip():
            return {"query": query, "results": [], "message": "检索问题不能为空"}
        with self._lock:
            if not self._ready:
                self.refresh()
            nodes = [node for group in self._nodes_by_path.values() for node in group]

            query_terms = _terms(query)
            query_set = set(query_terms)
            ranked: List[tuple[float, Dict[str, Any]]] = []
            for node in nodes:
                metadata = node["metadata"]
                if subsystem_id and metadata["subsystem_id"] != subsystem_id:
                    continue
                if knowledge_type and metadata["knowledge_type"] != knowledge_type:
                    continue
                node_terms = node["terms"]
                if not node_terms:
                    continue
                overlap = sum(node_terms.count(term) for term in query_set)
                if overlap == 0:
                    continue
                score = overlap / max(1, len(query_terms))
                if query.lower() in node["text"].lower():
                    score += 1.0
                if metadata["filename"].lower() in query.lower():
                    score += 0.5
                ranked.append((score, node))
            ranked.sort(key=lambda item: item[0], reverse=True)
            results = []
            for score, node in ranked[: max(1, min(top_k, 10))]:
                results.append({
                    "chunk_id": node["id"],
                    "source": node["metadata"]["source"],
                    "filename": node["metadata"]["filename"],
                    "subsystem_id": node["metadata"]["subsystem_id"],
                    "knowledge_type": node["metadata"]["knowledge_type"],
                    "chunk_index": node["metadata"]["chunk_index"],
                    "score": round(score, 4),
                    "content": node["text"][: settings.rag_result_chars],
                })
            response = {
                "query": query,
                "knowledge_base": "enterprise",
                "filters": {"subsystem_id": subsystem_id, "knowledge_type": knowledge_type},
                "results": results,
                "total": len(results),
                "message": "未找到高相关度内容" if not results else "检索完成",
            }
            log_event(
                f"RAG search subsystem={subsystem_id or '-'} type={knowledge_type or '-'} "
                f"candidates={len(nodes)} hits={len(results)} "
                f"elapsed_ms={(time.perf_counter() - started_at) * 1000:.1f}",
                source="rag",
            )
            return response

    def list_documents(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not self._ready:
                self.refresh()
            result = []
            for key, nodes in self._nodes_by_path.items():
                path = Path(key)
                metadata = self._metadata(path, self.root, "knowledge")
                result.append({
                    "source": path.relative_to(self.root).as_posix(),
                    "subsystem_id": metadata["subsystem_id"],
                    "knowledge_type": metadata["knowledge_type"],
                    "chunks": len(nodes),
                })
            return result


knowledge_service = KnowledgeService()
