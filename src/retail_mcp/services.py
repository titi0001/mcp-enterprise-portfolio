"""Permission-aware resource and tool managers."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from retail_mcp.audit import AuditLogger
from retail_mcp.cache import Cache
from retail_mcp.circuit_breaker import CircuitBreaker
from retail_mcp.domain import (
    CreateTicketInput,
    Customer,
    CustomerView,
    InventoryItem,
    InventoryUpdateInput,
    ProcessOrderInput,
    Sale,
    SupportTicket,
)
from retail_mcp.errors import NotFoundError
from retail_mcp.metrics import CACHE, LATENCY, REQUESTS
from retail_mcp.repository import RetailRepository
from retail_mcp.security import AuthenticationManager, Permission, Principal, Role

T = TypeVar("T")


class ResourceManager:
    def __init__(
        self,
        repository: RetailRepository,
        cache: Cache,
        audit: AuditLogger,
        cache_ttl_seconds: int,
        timeout_seconds: float,
        breaker: CircuitBreaker,
    ) -> None:
        self.repository = repository
        self.cache = cache
        self.audit = audit
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        self.breaker = breaker

    async def _cached(
        self,
        key: str,
        model: type[T],
        loader: Callable[[], Awaitable[T | None]],
    ) -> T | None:
        cached = await self.cache.get(key)
        if cached is not None:
            CACHE.labels("hit").inc()
            return model.model_validate(cached)  # type: ignore[attr-defined,no-any-return]
        CACHE.labels("miss").inc()
        async with asyncio.timeout(self.timeout_seconds):
            value = await self.breaker.call(loader)
        if value is not None:
            await self.cache.set(
                key,
                value.model_dump(mode="json"),  # type: ignore[attr-defined]
                self.cache_ttl_seconds,
            )
        return value

    async def customer(self, principal: Principal, customer_id: str) -> CustomerView:
        operation = "resource.customer"
        AuthenticationManager.authorize(principal, Permission.CUSTOMER_READ)
        with LATENCY.labels(operation).time():
            customer = await self._cached(
                f"customer:{customer_id}",
                Customer,
                lambda: self.repository.get_customer(customer_id),
            )
        if customer is None:
            REQUESTS.labels(operation, "not_found").inc()
            raise NotFoundError("Customer was not found")
        email = customer.email
        if principal.role == Role.SALES_ANALYST:
            local, _, domain = email.partition("@")
            email = f"{local[:1]}***@{domain}"
        result = CustomerView(
            id=customer.id,
            name=customer.name,
            email=email,
            tier=customer.tier,
            region=customer.region,
        )
        self.audit.emit(
            principal=principal,
            action="resource.read",
            target=f"customer:{customer_id}",
            outcome="success",
        )
        REQUESTS.labels(operation, "success").inc()
        return result

    async def inventory(self, principal: Principal, sku: str) -> InventoryItem:
        operation = "resource.inventory"
        AuthenticationManager.authorize(principal, Permission.INVENTORY_READ)
        with LATENCY.labels(operation).time():
            item = await self._cached(
                f"inventory:{sku}",
                InventoryItem,
                lambda: self.repository.get_inventory(sku),
            )
        if item is None:
            REQUESTS.labels(operation, "not_found").inc()
            raise NotFoundError("Inventory item was not found")
        self.audit.emit(
            principal=principal,
            action="resource.read",
            target=f"inventory:{sku}",
            outcome="success",
        )
        REQUESTS.labels(operation, "success").inc()
        return item

    async def sale(self, principal: Principal, sale_id: str) -> Sale:
        operation = "resource.sale"
        AuthenticationManager.authorize(principal, Permission.SALES_READ)
        with LATENCY.labels(operation).time():
            sale = await self._cached(
                f"sale:{sale_id}", Sale, lambda: self.repository.get_sale(sale_id)
            )
        if sale is None:
            REQUESTS.labels(operation, "not_found").inc()
            raise NotFoundError("Sale was not found")
        self.audit.emit(
            principal=principal,
            action="resource.read",
            target=f"sale:{sale_id}",
            outcome="success",
        )
        REQUESTS.labels(operation, "success").inc()
        return sale


class ToolManager:
    def __init__(
        self,
        repository: RetailRepository,
        cache: Cache,
        audit: AuditLogger,
        timeout_seconds: float,
    ) -> None:
        self.repository = repository
        self.cache = cache
        self.audit = audit
        self.timeout_seconds = timeout_seconds

    async def _run(
        self,
        principal: Principal,
        operation: str,
        target: str,
        function: Callable[[], Awaitable[T]],
    ) -> T:
        try:
            with LATENCY.labels(operation).time():
                async with asyncio.timeout(self.timeout_seconds):
                    result = await function()
        except Exception as exc:
            REQUESTS.labels(operation, "failure").inc()
            self.audit.emit(
                principal=principal,
                action=operation,
                target=target,
                outcome="failure",
                details={"error_type": type(exc).__name__},
            )
            raise
        REQUESTS.labels(operation, "success").inc()
        self.audit.emit(
            principal=principal,
            action=operation,
            target=target,
            outcome="success",
        )
        return result

    async def process_order(self, principal: Principal, data: ProcessOrderInput) -> Sale:
        AuthenticationManager.authorize(principal, Permission.ORDER_WRITE)
        result = await self._run(
            principal,
            "tool.process_order",
            f"customer:{data.customer_id}",
            lambda: self.repository.process_order(
                data.customer_id, data.sku, data.quantity, data.idempotency_key
            ),
        )
        await self.cache.delete(f"inventory:{data.sku}")
        await self.cache.delete(f"sale:{result.id}")
        return result

    async def update_inventory(
        self, principal: Principal, data: InventoryUpdateInput
    ) -> InventoryItem:
        AuthenticationManager.authorize(principal, Permission.INVENTORY_WRITE)
        result = await self._run(
            principal,
            "tool.update_inventory",
            f"inventory:{data.sku}",
            lambda: self.repository.update_inventory(data.sku, data.quantity_delta),
        )
        await self.cache.delete(f"inventory:{data.sku}")
        return result

    async def create_ticket(self, principal: Principal, data: CreateTicketInput) -> SupportTicket:
        AuthenticationManager.authorize(principal, Permission.TICKET_WRITE)
        return await self._run(
            principal,
            "tool.create_support_ticket",
            f"customer:{data.customer_id}",
            lambda: self.repository.create_ticket(
                data.customer_id, data.subject, data.description, data.priority
            ),
        )
