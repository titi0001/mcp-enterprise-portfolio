# Enterprise security framework

## Control model

Authentication is performed at the HTTP boundary. API keys are hashed in memory and compared in constant time. The current principal is propagated in a context variable, and every resource or tool independently checks a permission before accessing data. This prevents an AI prompt from changing authorization decisions.

For a mature enterprise deployment, replace bootstrap API keys with OAuth 2.1 at the transport layer, protected-resource metadata, audience-bound tokens, and the corporate identity provider. The API-key implementation satisfies the portfolio scenario and creates a narrow replacement boundary.

## Role matrix

| Capability | Customer service | Inventory manager | Sales analyst | Admin |
|---|:---:|:---:|:---:|:---:|
| Read customer | Yes | No | Masked PII | Yes |
| Read inventory | Yes | Yes | Yes | Yes |
| Update inventory | No | Yes | No | Yes |
| Read sales | No | Yes | Yes | Yes |
| Process order | No | No | No | Yes |
| Create support ticket | Yes | No | No | Yes |

## Threat controls

- **Prompt injection:** Retrieved content is treated as data; server permissions and schemas remain authoritative.
- **Data exfiltration:** Field-level PII filtering and resource-specific permissions minimize returned data.
- **Tool misuse:** Tool arguments are typed, length-bounded, validated, audited, and executed transactionally.
- **Replay/duplicate writes:** Order processing requires an idempotency key enforced by a unique constraint.
- **Credential theft:** TLS, secret injection, rotation, no query-string credentials, and no key logging.
- **Denial of service:** Gateway and per-principal rate limits, body limits, timeouts, pool limits, and autoscaling.
- **Tenant crossover:** A production extension must include tenant identity in the principal, database policy, and cache key before multi-tenancy is enabled.
- **Supply chain:** Locked dependencies, dependency review, image scanning, and signed images are release gates.

## Audit policy

Audit events include timestamp, request ID, subject, role, action, target, outcome, and error type. They deliberately exclude prompts, API keys, customer email, and tool descriptions. Production logs should be immutable, encrypted, access-controlled, exported to the enterprise SIEM, and retained according to legal policy.

## Secure release checklist

- Development credentials are rejected in production mode.
- Secrets come from a managed secret store and have a tested rotation procedure.
- TLS certificates and cipher policy are validated.
- Authorization denial tests cover every role and operation.
- Dependency and container vulnerability scans have no unaccepted critical findings.
- Logs contain no credentials or unnecessary PII.
- Backup restoration and incident escalation are tested.

