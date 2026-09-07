#!/usr/bin/env python3
"""Copy the phase-one public corpus into the explicit COMMON knowledge bases."""
from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "datasets" / "external"
KNOWLEDGE = ROOT / "knowledge" / "COMMON"


def document_id(prefix: str, name: str) -> str:
    return f"{prefix}_{re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_').upper()}"


def copy_document(source: Path, destination: Path, knowledge_type: str, prefix: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    title = source.stem.replace("_", " ").replace("-", " ").title()
    front_matter = (
        "---\n"
        f"id: {document_id(prefix, source.stem)}\n"
        f"title: {title}\n"
        "subsystem: COMMON\n"
        f"knowledge_type: {knowledge_type}\n"
        "source: external\n"
        f"source_path: {source.relative_to(ROOT).as_posix()}\n"
        "version: external\n"
        "language: en\n"
        f"trust_level: {'curated' if knowledge_type == 'runbook' else 'evidence'}\n"
        "---\n\n"
    )
    text = source.read_text(encoding="utf-8", errors="replace")
    destination.write_text(front_matter + text, encoding="utf-8")


def main() -> None:
    runbooks = EXTERNAL / "incident-response-on-call-agent" / "runbooks"
    references = EXTERNAL / "opentelemetry-skill" / "references"
    copied = 0
    for source in sorted(runbooks.glob("*.md")):
        copy_document(source, KNOWLEDGE / "runbook" / source.name, "runbook", "RUNBOOK")
        copied += 1
    for source in sorted(references.rglob("*.md")):
        name = "__".join(source.relative_to(references).parts)
        copy_document(source, KNOWLEDGE / "reference" / name, "reference", "OTEL")
        copied += 1
    print(f"normalized {copied} documents into {KNOWLEDGE}")


if __name__ == "__main__":
    main()
