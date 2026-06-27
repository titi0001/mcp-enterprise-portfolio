# Portfolio presentation outline

1. **Business problem:** fragmented retail integrations and governed AI access.
2. **Executive recommendation:** MCP as a controlled AI capability layer, not a replacement for systems of record.
3. **Architecture:** host, gateway, six internal server components, data adapters, and observability.
4. **Live demonstration:** authenticate, read filtered customer/inventory resources, create a ticket, show denied inventory update, then show metrics and audit event.
5. **Security:** trust boundaries, RBAC matrix, PII filtering, idempotency, TLS, and secret lifecycle.
6. **Production operations:** containers, Kubernetes, CI/CD, SLOs, dashboards, alerts, and rollback.
7. **Risk and ROI:** highest risks, mitigations, phased timeline, and measurable benefits.
8. **Trade-offs:** API keys versus OAuth, projection database versus direct calls, stateless scaling versus session features.
9. **Roadmap:** enterprise IdP/OAuth, tenant isolation, event-driven synchronization, load testing, and regional failover.

## Demonstration acceptance criteria

- MCP client lists three resources, three tools, and one prompt.
- Each role receives only authorized results.
- Sales analyst customer email is masked.
- Repeating an order idempotency key does not duplicate the sale or inventory decrement.
- Failed operations return safe errors and produce audit/metric evidence.
- Readiness changes when a required dependency is unavailable.
