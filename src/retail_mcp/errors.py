"""Domain errors with safe messages for MCP clients."""


class RetailMCPError(Exception):
    """Base error whose message is safe to return to a client."""

    code = "internal_error"

    def __init__(self, message: str = "The request could not be completed") -> None:
        self.public_message = message
        super().__init__(message)


class AuthenticationError(RetailMCPError):
    code = "authentication_failed"


class AuthorizationError(RetailMCPError):
    code = "permission_denied"


class NotFoundError(RetailMCPError):
    code = "not_found"


class ConflictError(RetailMCPError):
    code = "conflict"


class DependencyUnavailableError(RetailMCPError):
    code = "dependency_unavailable"


class RateLimitError(RetailMCPError):
    code = "rate_limit_exceeded"

