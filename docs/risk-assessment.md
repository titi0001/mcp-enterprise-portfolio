# Risk assessment

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---:|---:|---|---|
| Prompt injection triggers unsafe action | Medium | Critical | Server-side RBAC, strict schemas, tool allowlists, confirmation for high-impact actions | Security |
| Customer data leaks across roles | Low | Critical | Per-request authorization, PII filtering, negative authorization tests | Data owner |
| API key exposure | Medium | High | Secret manager, rotation, short validity, TLS, no credential logging | IAM |
| Duplicate order after retry | Medium | High | Required idempotency key and unique database constraint | Application |
| Dependency outage cascades | Medium | High | Timeouts, circuit breaker, bounded pool, graceful errors | SRE |
| Cache returns stale inventory | Medium | Medium | Short TTL and invalidation after writes | Inventory |
| Cache bypasses authorization | Low | Critical | Authorize before lookup; cache raw data and filter after retrieval | Application |
| Excessive tool catalog reduces AI accuracy | Medium | Medium | Minimal role-specific capability sets | Product |
| Audit logs contain sensitive content | Medium | High | Metadata-only audit events, access controls, retention policy | Compliance |
| SDK/protocol breaking change | Medium | Medium | Pin MCP v1 below v2, compatibility tests, planned migration | Platform |
| Traffic spike exhausts database | Medium | High | Rate limits, cache, pool limits, HPA and load testing | SRE |
| Region loss | Low | Critical | Backups, cross-region restore tests, documented failover | Infrastructure |

Risks are reviewed quarterly and before exposing a new resource or tool. Critical risks require evidence that controls were tested before production approval.

