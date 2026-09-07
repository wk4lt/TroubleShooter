---
id: RUNBOOK_REDIS_CONNECTION_FAILURE
title: Redis Connection Failure
subsystem: COMMON
knowledge_type: runbook
source: external
source_path: datasets/external/incident-response-on-call-agent/runbooks/redis_connection_failure.md
version: external
language: en
trust_level: curated
---

# Runbook: Redis Connection Failure

## Symptoms
- Service logs show "ECONNREFUSED 127.0.0.1:6379"
- Session store unavailable
- Auth failures across all services
- Metrics: error_rate near 100%, low CPU (not computing, just failing)

## Common Causes
1. Redis pod OOMKilled — evicted due to memory pressure
2. Redis cluster failover failed silently
3. Network policy change blocking Redis port 6379
4. Redis maxmemory limit hit — evicting keys aggressively

## Immediate Mitigation
1. Check Redis status:
   kubectl get pods -n cache | grep redis
   redis-cli -h <host> ping
2. Check Redis memory:
   redis-cli INFO memory | grep used_memory_human
3. Restart Redis if OOMKilled:
   kubectl rollout restart deployment/redis
4. Force service reconnect:
   kubectl rollout restart deployment/<affected-service>

## Auto-Remediation Steps
- restart_service("redis") — restart the Redis pod
- restart_service("<affected-service>") — force reconnect after Redis recovers
- clear_cache() — if memory pressure is the cause

## Escalation
Page: platform-oncall
This is typically P0 — auth depends on Redis

## Prevention
- Set Redis memory alert at 80% utilization
- Configure Redis maxmemory-policy = allkeys-lru
- Add Redis sentinel or cluster for HA
- Health check Redis in service startup probe