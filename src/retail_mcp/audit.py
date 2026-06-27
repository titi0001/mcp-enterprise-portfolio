"""Structured security audit events."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from retail_mcp.security import Principal, current_request_id

audit_log = logging.getLogger("retail_mcp.audit")


class AuditLogger:
    def emit(
        self,
        *,
        principal: Principal,
        action: str,
        target: str,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": current_request_id(),
            "subject": principal.subject,
            "role": principal.role.value,
            "action": action,
            "target": target,
            "outcome": outcome,
            "details": details or {},
        }
        audit_log.info(json.dumps(event, separators=(",", ":"), default=str))
