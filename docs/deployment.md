# Deployment and operations guide

## Local development

```bash
asdf install
cp .env.example .env
uv sync --python "$(asdf which python)" --extra dev
uv run retail-mcp --transport http
```

The endpoints are:

- MCP Streamable HTTP: `http://localhost:8000/mcp`
- Liveness: `http://localhost:8000/health/live`
- Readiness: `http://localhost:8000/health/ready`
- Prometheus metrics: `http://localhost:8000/metrics`

Development keys are documented only for local use. Never expose development mode outside a workstation.

## Integrated environment

```bash
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health/ready
```

Grafana runs on port 3000 and Prometheus on 9090. PostgreSQL initializes from `migrations/001_init.sql` only when its data volume is new.

## Production Compose

Provide `DATABASE_URL`, `REDIS_URL`, `RETAIL_MCP_API_KEYS`, `TLS_CERT_DIR`, and a strong `GRAFANA_ADMIN_PASSWORD` through the deployment secret system, then run:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Kubernetes

1. Replace the example image path in `deploy/k8s/deployment.yaml` with an immutable digest.
2. Create `retail-mcp-secrets` through the organization secret controller, not a committed YAML file.
3. Provision `retail-mcp-tls` using the approved certificate controller.
4. Deploy managed PostgreSQL and Redis with encryption, backups, and private networking.
5. Apply the manifest and verify rollout, probes, alerts, and an MCP protocol smoke test.

## SLOs and capacity

- Availability: 99.9% monthly for read operations.
- p95 server latency: below 500 ms excluding source-system latency.
- Tool failure rate: below 1%, excluding valid business rejections.
- Audit event delivery: 99.99% with alerts on pipeline failure.
- Recovery time objective: 60 minutes; recovery point objective: 15 minutes.

Load-test each release at twice expected peak request rate. Increase replicas before increasing the database pool; total connections across all replicas must remain below the database limit with operating headroom.

## Rollback

Deploy immutable images, retain the previous version, and use rolling or canary deployment. Database changes must be backward compatible for at least one release. If error or latency thresholds are exceeded, route traffic to the previous image and preserve failed-version audit evidence for analysis.
