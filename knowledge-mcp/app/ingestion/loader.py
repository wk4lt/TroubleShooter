from __future__ import annotations

from pathlib import Path

from app.ingestion.metadata import build_metadata, split_front_matter
from app.models.document import KnowledgeDocument


TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".rst"}


def load_documents(root: Path) -> list[KnowledgeDocument]:
    documents: list[KnowledgeDocument] = []
    if not root.exists():
        return documents
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        front_matter, text = split_front_matter(source)
        metadata = build_metadata(path, root, front_matter)
        documents.append(
            KnowledgeDocument(
                doc_id=metadata["doc_id"], title=metadata["title"], text=text.strip(),
                source_path=metadata["source_path"], metadata=metadata, path=path,
            )
        )
    return documents
