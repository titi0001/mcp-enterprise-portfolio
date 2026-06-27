"""Low-cardinality Prometheus metrics."""

from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter(
    "retail_mcp_requests_total",
    "MCP requests by operation and outcome",
    ("operation", "outcome"),
)
LATENCY = Histogram(
    "retail_mcp_request_duration_seconds",
    "MCP operation latency",
    ("operation",),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
CACHE = Counter("retail_mcp_cache_total", "Cache outcomes", ("outcome",))
DEPENDENCY_HEALTH = Gauge(
    "retail_mcp_dependency_health", "Dependency health (1 healthy, 0 unhealthy)", ("dependency",)
)
IN_FLIGHT = Gauge("retail_mcp_in_flight_requests", "MCP requests currently in flight")

