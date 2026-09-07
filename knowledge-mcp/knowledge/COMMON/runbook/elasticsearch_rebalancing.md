---
id: RUNBOOK_ELASTICSEARCH_REBALANCING
title: Elasticsearch Rebalancing
subsystem: COMMON
knowledge_type: runbook
source: external
source_path: datasets/external/incident-response-on-call-agent/runbooks/elasticsearch_rebalancing.md
version: external
language: en
trust_level: curated
---

# Runbook: Elasticsearch Shard Rebalancing

## Symptoms
- Search latency elevated (p99 > 2s)
- ES cluster health: YELLOW
- Logs: "Cluster health: YELLOW — shards relocating"
- Metrics: high CPU, elevated memory on ES nodes

## Common Causes
1. ES node restart triggered automatic shard rebalancing
2. New index created with too many shards
3. Hot-spotting — uneven shard distribution

## Immediate Mitigation
1. Check cluster health:
   curl http://localhost:9200/_cluster/health?pretty
2. Check shard allocation:
   curl http://localhost:9200/_cat/shards?v | grep RELOCATING
3. If rebalancing is the cause — wait 10-15 min (usually self-resolving)
4. To speed up rebalancing:
   PUT /_cluster/settings
   {"transient": {"cluster.routing.allocation.cluster_concurrent_rebalance": 4}}
5. To temporarily pause rebalancing (reduces load, slows recovery):
   PUT /_cluster/settings
   {"transient": {"cluster.routing.rebalance.enable": "none"}}

## Auto-Remediation Steps
- scale_pods("elasticsearch") — add capacity to absorb rebalancing load
- This is typically self-resolving — monitor for 15 min before acting

## Escalation
Page: search-oncall
Escalate to platform-oncall if cluster goes RED

## Prevention
- Alert on ES cluster YELLOW status
- Schedule rebalancing during low-traffic windows
- Use ILM policies to manage index lifecycle