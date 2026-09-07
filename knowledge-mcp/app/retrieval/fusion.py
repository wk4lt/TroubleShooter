from __future__ import annotations

from collections import defaultdict


def reciprocal_rank_fusion(rankings: dict[str, list[str]], k: int, top_k: int) -> list[tuple[str, float, list[str]]]:
    scores: dict[str, float] = defaultdict(float)
    sources: dict[str, list[str]] = defaultdict(list)
    for source, node_ids in rankings.items():
        for rank, node_id in enumerate(node_ids, start=1):
            scores[node_id] += 1 / (k + rank)
            sources[node_id].append(source)
    ordered = sorted(scores, key=lambda node_id: (-scores[node_id], node_id))[:top_k]
    return [(node_id, scores[node_id], sources[node_id]) for node_id in ordered]
