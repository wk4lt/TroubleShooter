---
id: RUNBOOK_DB_CONNECTION_POOL
title: Db Connection Pool
subsystem: COMMON
knowledge_type: runbook
source: external
source_path: datasets/external/incident-response-on-call-agent/runbooks/db_connection_pool.md
version: external
language: en
trust_level: curated
---

# Runbook: Database Connection Pool Exhaustion

## Symptoms
- Service logs show "connection pool timeout after 30000ms"
- DB CPU is normal but active connections at maximum
- Latency spike on all DB-dependent endpoints
- Metrics: db_pool_used approaching db_pool_max

## Common Causes
1. Missing index causing full table scans — queries hold connections longer
2. N+1 query pattern introduced in recent deployment
3. Traffic spike exceeding pool capacity
4. Connection leak — connections not being returned to pool

## Immediate Mitigation (under 5 minutes)
1. Check current pool utilization:
   kubectl exec -it <pod> -- curl localhost:8080/metrics | grep db_pool
2. Identify slow queries:
   SELECT pid, query, state, query_start FROM pg_stat_activity WHERE state != 'idle' ORDER BY query_start;
3. Temporarily increase pool size (stop-gap only):
   kubectl set env deployment/<service> DB_POOL_SIZE=100
4. If no improvement in 2 minutes — rollback:
   kubectl rollout undo deployment/<service>

## Root Cause Investigation
- Check for missing indexes: EXPLAIN ANALYZE <slow query>
- Review recent deployments: kubectl rollout history deployment/<service>
- Check APM traces for N+1 patterns

## Auto-Remediation Steps
- restart_service() — clears all connections, forces reconnect
- rollback_deployment() — if issue introduced by recent deploy
- scale_pods() — if traffic spike is the cause

## Escalation
Page: database-oncall
If rollback doesn't resolve in 10 min: page platform-oncall

## Prevention
- Add index coverage check to CI pipeline
- Alert at 70% pool utilization (before saturation)
- Add DB query timeout at application layer (max 5s)
- Load test with production query patterns before deploys