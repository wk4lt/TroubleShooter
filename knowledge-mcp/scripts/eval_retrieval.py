#!/usr/bin/env python3
"""Evaluate retrieval and optionally Agent decisions from JSONL predictions."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.config import ROOT, load_settings
from app.runtime.knowledge_runtime import KnowledgeRuntime


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


async def evaluate_retrieval(runtime: KnowledgeRuntime, cases: list[dict]) -> dict[str, float]:
    ranks: list[int] = []
    routers: list[bool] = []
    for case in cases:
        payload = await runtime.search(case["query"], top_k=10)
        expected = set(case.get("expected_docs", []))
        names = [Path(item["source_path"]).name for item in payload["results"]]
        rank = next((index + 1 for index, name in enumerate(names) if name in expected), 0)
        ranks.append(rank)
        expected_type = case.get("expected_type")
        if expected_type:
            routers.append(expected_type in payload["router"]["knowledge_types"] or any(
                expected_type in selected for selected in payload["router"]["selected"]
            ))
    count = len(cases) or 1
    return {
        "router_accuracy": round(sum(routers) / len(routers), 4) if routers else 0.0,
        "recall_at_1": round(sum(rank <= 1 and rank > 0 for rank in ranks) / count, 4),
        "recall_at_5": round(sum(rank <= 5 and rank > 0 for rank in ranks) / count, 4),
        "recall_at_10": round(sum(rank <= 10 and rank > 0 for rank in ranks) / count, 4),
        "mrr": round(sum(1 / rank for rank in ranks if rank) / count, 4),
    }


def evaluate_agent_decisions(expected: list[dict], predictions: list[dict]) -> dict[str, float]:
    by_id = {item["id"]: item for item in predictions}
    matched = [item for item in expected if item["id"] in by_id]
    count = len(matched) or 1
    return {
        "first_tool_accuracy": round(sum(
            by_id[item["id"]].get("first_tool") == item.get("expected_first_tool") for item in matched
        ) / count, 4),
        "next_tool_accuracy": round(sum(
            by_id[item["id"]].get("next_tool") == item.get("expected_next_tool") for item in matched
        ) / count, 4),
        "final_decision_accuracy": round(sum(
            by_id[item["id"]].get("final_decision") == item.get("expected_final_decision") for item in matched
        ) / count, 4),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "evals" / "retrieval.jsonl"))
    parser.add_argument("--agent-predictions")
    args = parser.parse_args()
    runtime = KnowledgeRuntime(load_settings())
    print(json.dumps(await evaluate_retrieval(runtime, load_jsonl(Path(args.dataset))), indent=2))
    if args.agent_predictions:
        expected = load_jsonl(ROOT / "evals" / "agent_decision.jsonl")
        print(json.dumps(evaluate_agent_decisions(expected, load_jsonl(Path(args.agent_predictions))), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
