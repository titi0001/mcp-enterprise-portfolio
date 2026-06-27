# ROI and implementation timeline

## Illustrative business case

Assumptions must be replaced with the retailer's measured values before approval:

- 100 customer-service agents.
- 30 interactions per agent per day, 250 working days per year.
- Two minutes saved per assisted interaction.
- Fully loaded agent cost of USD 30 per hour.
- Initial implementation cost of USD 180,000 and annual platform cost of USD 60,000.

Estimated annual productivity capacity: `100 × 30 × 250 × 2 / 60 = 25,000 hours`, equivalent to USD 750,000. After annual platform cost, the illustrative first-year gross benefit is USD 690,000. Against the initial implementation cost, illustrative payback is approximately four months after launch. This is capacity released, not guaranteed cash savings; finance must validate utilization and benefit realization.

## Timeline

| Phase | Weeks | Exit criteria |
|---|---:|---|
| Discovery and data governance | 1–3 | Owners, classifications, SLOs, use cases approved |
| Read-only architecture pilot | 4–7 | Customer and inventory resources pass security testing |
| Controlled tools | 8–11 | Idempotency, confirmation, rollback, and audit verified |
| Production hardening | 12–14 | Load, recovery, penetration, and operational tests pass |
| Limited rollout | 15–17 | KPIs meet target with 10–20 users |
| Scale and optimize | 18+ | Phased expansion under change control |

## KPIs

- Integration lead time and cost per new AI channel.
- Customer-service average handling time and first-contact resolution.
- Tool success, rejection, and rollback rates.
- p95 latency, availability, cache hit ratio, and mean time to recovery.
- Security policy violations and confirmed data incidents.
