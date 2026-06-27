"""MCP resources, tools, and prompts."""

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import Context, FastMCP

from retail_mcp.bootstrap import ApplicationContainer, build_container
from retail_mcp.config import get_settings
from retail_mcp.domain import CreateTicketInput, InventoryUpdateInput, ProcessOrderInput
from retail_mcp.errors import AuthenticationError, RetailMCPError
from retail_mcp.security import AuthenticationManager, Principal, current_principal

settings = get_settings()
authentication = AuthenticationManager(settings.api_keys)
runtime: ApplicationContainer | None = None


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[ApplicationContainer]:
    global runtime
    if runtime is not None:
        yield runtime
        return
    container = await build_container(settings, authentication)
    runtime = container
    try:
        yield container
    finally:
        runtime = None
        await container.close()


mcp = FastMCP(
    "Retail Enterprise MCP",
    instructions=(
        "Secure access to customer, inventory, sales, and support operations. "
        "Never infer authorization; the server enforces permissions."
    ),
    lifespan=lifespan,
    stateless_http=True,
    json_response=True,
    streamable_http_path="/mcp",
)


def _container(ctx: Context) -> ApplicationContainer:
    return ctx.request_context.lifespan_context


def _principal() -> Principal:
    try:
        return current_principal()
    except AuthenticationError:
        # STDIO has no HTTP headers; its credential is injected via the environment.
        return authentication.authenticate(settings.stdio_api_key)


def _safe_error(exc: Exception) -> ValueError:
    if isinstance(exc, RetailMCPError):
        return ValueError(f"{exc.code}: {exc.public_message}")
    logging.getLogger(__name__).exception("Unhandled MCP operation failure")
    return ValueError("internal_error: The request could not be completed")


@mcp.resource("retail://customers/{customer_id}", mime_type="application/json")
async def customer_resource(customer_id: str, ctx: Context) -> str:
    """Return a permission-filtered customer record."""
    try:
        value = await _container(ctx).resources.customer(_principal(), customer_id)
        return value.model_dump_json()
    except Exception as exc:
        raise _safe_error(exc) from None


@mcp.resource("retail://inventory/{sku}", mime_type="application/json")
async def inventory_resource(sku: str, ctx: Context) -> str:
    """Return current inventory and reorder information for a SKU."""
    try:
        value = await _container(ctx).resources.inventory(_principal(), sku.upper())
        return value.model_dump_json()
    except Exception as exc:
        raise _safe_error(exc) from None


@mcp.resource("retail://sales/{sale_id}", mime_type="application/json")
async def sale_resource(sale_id: str, ctx: Context) -> str:
    """Return a sale record when the caller has sales access."""
    try:
        value = await _container(ctx).resources.sale(_principal(), sale_id)
        return value.model_dump_json()
    except Exception as exc:
        raise _safe_error(exc) from None


@mcp.tool()
async def process_order(
    customer_id: str,
    sku: str,
    quantity: int,
    idempotency_key: str,
    ctx: Context,
) -> dict[str, object]:
    """Create an order atomically and decrement inventory. Requires order:write."""
    try:
        data = ProcessOrderInput(
            customer_id=customer_id,
            sku=sku.upper(),
            quantity=quantity,
            idempotency_key=idempotency_key,
        )
        result = await _container(ctx).tools.process_order(_principal(), data)
        return result.model_dump(mode="json")
    except Exception as exc:
        raise _safe_error(exc) from None


@mcp.tool()
async def update_inventory(
    sku: str,
    quantity_delta: int,
    reason: str,
    ctx: Context,
) -> dict[str, object]:
    """Adjust inventory with validation and audit logging. Requires inventory:write."""
    try:
        data = InventoryUpdateInput(sku=sku.upper(), quantity_delta=quantity_delta, reason=reason)
        result = await _container(ctx).tools.update_inventory(_principal(), data)
        return result.model_dump(mode="json")
    except Exception as exc:
        raise _safe_error(exc) from None


@mcp.tool()
async def create_support_ticket(
    customer_id: str,
    subject: str,
    description: str,
    priority: str = "normal",
    *,
    ctx: Context,
) -> dict[str, object]:
    """Create a customer support ticket. Requires ticket:write."""
    try:
        data = CreateTicketInput(
            customer_id=customer_id,
            subject=subject,
            description=description,
            priority=priority,
        )
        result = await _container(ctx).tools.create_ticket(_principal(), data)
        return result.model_dump(mode="json")
    except Exception as exc:
        raise _safe_error(exc) from None


@mcp.prompt()
def investigate_customer_issue(customer_id: str) -> str:
    """Guide a support investigation without authorizing any operation."""
    return json.dumps(
        {
            "objective": "Investigate a customer issue safely",
            "customer_resource": f"retail://customers/{customer_id}",
            "steps": [
                "Read the customer resource if authorized",
                "Ask for missing facts instead of guessing",
                "Use create_support_ticket only after user confirmation",
                "Do not expose credentials or unrelated customer data",
            ],
        }
    )
