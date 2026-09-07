from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


VALID_TYPES = {"design_doc", "runbook", "issue", "fault_case", "reference", "manual"}


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    values = yaml.safe_load(match.group(1)) or {}
    return values if isinstance(values, dict) else {}, match.group(2)


def build_metadata(path: Path, root: Path, front_matter: dict[str, Any]) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    parts = relative.split("/")
    subsystem = str(front_matter.get("subsystem") or (parts[0] if len(parts) >= 3 else "COMMON")).upper()
    inferred_type = parts[1] if len(parts) >= 3 else "reference"
    knowledge_type = str(front_matter.get("knowledge_type") or inferred_type).lower()
    if knowledge_type not in VALID_TYPES:
        raise ValueError(f"unsupported knowledge_type '{knowledge_type}' in {relative}")
    doc_id = str(front_matter.get("id") or f"{subsystem}_{path.stem}".upper())
    title = str(front_matter.get("title") or path.stem.replace("_", " ").title())
    tags = front_matter.get("tags") or []
    if not isinstance(tags, list):
        tags = [str(tags)]
    return {
        "doc_id": doc_id,
        "title": title,
        "subsystem": subsystem,
        "knowledge_type": knowledge_type,
        "source": str(front_matter.get("source") or "local"),
        "source_path": relative,
        "version": str(front_matter.get("version") or "1.0"),
        "tags": [str(tag) for tag in tags],
        "language": str(front_matter.get("language") or "en"),
        "trust_level": str(front_matter.get("trust_level") or ("curated" if knowledge_type == "runbook" else "evidence")),
    }
