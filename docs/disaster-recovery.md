# Disaster recovery and business continuity

## Objectives

- Recovery time objective (RTO): 60 minutes.
- Recovery point objective (RPO): 15 minutes.
- MCP compute is disposable and rebuilt from signed images and configuration.
- PostgreSQL is the durable state requiring point-in-time recovery.
- Redis is reconstructible and is not a system of record.

## Backup policy

- Continuous PostgreSQL write-ahead-log archiving plus daily encrypted snapshots.
- Cross-region backup copy with separate access controls.
- Configuration, dashboards, and manifests versioned in Git.
- Secret values backed up only through the secret-management platform.
- Monthly automated restore validation and quarterly operator recovery exercise.

## Recovery procedure

1. Declare the incident and assign incident commander, communications lead, and recovery lead.
2. Disable write tools if data consistency is uncertain; keep safe reads only when approved.
3. Provision clean infrastructure from version-controlled manifests.
4. Restore PostgreSQL to the approved point and run integrity checks.
5. Start Redis empty, deploy MCP replicas, and warm only safe high-value cache entries.
6. Run authentication, authorization, resource, tool-idempotency, and audit smoke tests.
7. Restore traffic gradually while monitoring errors, latency, and dependency health.
8. Reconcile orders and inventory created around the incident window.
9. Close recovery only after business and security owners approve.

## Degraded modes

- Redis unavailable: local development can use memory cache; production returns controlled dependency errors until shared cache is restored or an approved bypass is deployed.
- PostgreSQL unavailable: readiness fails and the gateway removes the replica; no write operation is attempted.
- Audit pipeline unavailable: retain local buffered logs where supported and disable high-risk writes if auditability cannot be guaranteed.
- Source system unavailable: circuit breaker stops repeated calls and the server returns a sanitized temporary-unavailability error.

