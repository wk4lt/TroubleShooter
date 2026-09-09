"""Import OpenViking repository documentation through the existing official adapter.

This deliberately imports documentation only. CodeGraph remains the source of code facts.

Example:
    PYTHONPATH=backend backend/.venv/bin/python backend/scripts/import_openviking_demo.py \
      --repo /opt/src/OpenViking
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import List, Tuple


DEFAULT_TARGET_URI = "viking://resources/openviking-demo"
DOCUMENT_ROOTS = ("docs", "architecture", "concepts", "api", "guides", "design", "adr")


def collect_document_sources(repository: Path) -> List[Tuple[Path, str]]:
    """Return non-overlapping documentation sources and their target suffixes."""
    sources: List[Tuple[Path, str]] = []
    readme = repository / "README.md"
    if readme.is_file():
        sources.append((readme, "README.md"))
    for name in DOCUMENT_ROOTS:
        candidate = repository / name
        if candidate.is_dir():
            sources.append((candidate, name))
    return sources


def target_uri(base_uri: str, suffix: str) -> str:
    return f"{base_uri.rstrip('/')}/{suffix}"


async def import_documents(repository: Path, resource_uri: str) -> List[dict]:
    from app.context.openviking_adapter import OpenVikingAdapter

    adapter = OpenVikingAdapter()
    try:
        results = []
        for source, suffix in collect_document_sources(repository):
            destination = target_uri(resource_uri, suffix)
            result = await adapter.import_resource(source, target_uri=destination, wait=True)
            results.append({"source": str(source), "target_uri": destination, "result": result})
        return results
    finally:
        await adapter.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import OpenViking repository documentation using the official OpenViking adapter."
    )
    parser.add_argument(
        "--repo",
        default=os.getenv("OPENVIKING_DEMO_REPO", ""),
        help="Path to a local clone of https://github.com/volcengine/OpenViking (or OPENVIKING_DEMO_REPO).",
    )
    parser.add_argument(
        "--resource-uri",
        default=os.getenv("OPENVIKING_RESOURCE_URI", DEFAULT_TARGET_URI),
        help="OpenViking resource URI; must match OPENVIKING_RESOURCE_URI used by the Runtime.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show selected documentation without importing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repository = Path(args.repo).expanduser().resolve() if args.repo else None
    if repository is None or not repository.is_dir():
        raise SystemExit("--repo (or OPENVIKING_DEMO_REPO) must be an existing OpenViking checkout")
    if not args.resource_uri.startswith("viking://resources/"):
        raise SystemExit("--resource-uri must begin with viking://resources/")

    sources = collect_document_sources(repository)
    if not sources:
        raise SystemExit(
            "No README.md or documentation root (docs/, architecture/, concepts/, api/, guides/, design/, adr/) was found"
        )

    if args.dry_run:
        for source, suffix in sources:
            print({"source": str(source), "target_uri": target_uri(args.resource_uri, suffix)})
        return

    for imported in asyncio.run(import_documents(repository, args.resource_uri)):
        print(imported)


if __name__ == "__main__":
    main()
