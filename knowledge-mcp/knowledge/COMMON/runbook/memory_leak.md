---
id: RUNBOOK_MEMORY_LEAK
title: Memory Leak
subsystem: COMMON
knowledge_type: runbook
source: external
source_path: datasets/external/incident-response-on-call-agent/runbooks/memory_leak.md
version: external
language: en
trust_level: curated
---

# Runbook: Memory Leak / OOMKilled

## Symptoms
- Container memory_mb metric growing steadily
- Pod eventually OOMKilled and restarted
- Periodic brief outages (pod restart cycle)

## Immediate Mitigation
1. Check memory trend:
   kubectl top pods | grep <service>
2. If memory near limit — restart now before OOMKill:
   kubectl rollout restart deployment/<service>
3. Increase memory limit temporarily:
   kubectl set resources deployment/<service> --limits=memory=1Gi

## Root Cause Investigation
- Check if memory grew after recent deployment
- Profile heap: attach async-profiler or use JVM heap dump
- Check for event listener leaks, unclosed DB cursors, large caches

## Auto-Remediation Steps
- restart_service() — temporary fix, buys time
- rollback_deployment() — if leak introduced by recent deploy

## Prevention
- Add memory growth alert (>80% of limit)
- Add memory leak detection to staging load tests