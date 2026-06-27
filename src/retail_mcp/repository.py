"""Repository ports and adapters for retail systems of record."""

import asyncio
from decimal import Decimal
from typing import Any, Protocol
from uuid import uuid4

from retail_mcp.database import PostgresConnectionPool
from retail_mcp.domain import (
    Customer,
    CustomerTier,
    InventoryItem,
    Sale,
    SaleStatus,
    SupportTicket,
    TicketStatus,
    utc_now,
)
from retail_mcp.errors import ConflictError, NotFoundError


class RetailRepository(Protocol):
    async def get_customer(self, customer_id: str) -> Customer | None: ...

    async def get_inventory(self, sku: str) -> InventoryItem | None: ...

    async def get_sale(self, sale_id: str) -> Sale | None: ...

    async def process_order(
        self, customer_id: str, sku: str, quantity: int, idempotency_key: str
    ) -> Sale: ...

    async def update_inventory(self, sku: str, quantity_delta: int) -> InventoryItem: ...

    async def create_ticket(
        self, customer_id: str, subject: str, description: str, priority: str
    ) -> SupportTicket: ...

    async def health(self) -> bool: ...

    async def close(self) -> None: ...


class InMemoryRetailRepository:
    """Deterministic adapter for development and tests with atomic writes."""

    def __init__(self) -> None:
        now = utc_now()
        self.customers = {
            "cus_1001": Customer(
                id="cus_1001",
                name="Ana Silva",
                email="ana.silva@example.com",
                tier=CustomerTier.GOLD,
                region="BR-SP",
                created_at=now,
            ),
            "cus_1002": Customer(
                id="cus_1002",
                name="Carlos Lima",
                email="carlos.lima@example.com",
                tier=CustomerTier.STANDARD,
                region="BR-RJ",
                created_at=now,
            ),
        }
        self.inventory = {
            "SKU-RED-01": InventoryItem(
                sku="SKU-RED-01",
                name="Red Running Shoe",
                quantity=50,
                reorder_level=10,
                unit_price=Decimal("129.90"),
                updated_at=now,
            ),
            "SKU-BAG-02": InventoryItem(
                sku="SKU-BAG-02",
                name="Urban Backpack",
                quantity=25,
                reorder_level=5,
                unit_price=Decimal("89.50"),
                updated_at=now,
            ),
        }
        self.sales: dict[str, Sale] = {}
        self.tickets: dict[str, SupportTicket] = {}
        self.idempotency: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def get_customer(self, customer_id: str) -> Customer | None:
        return self.customers.get(customer_id)

    async def get_inventory(self, sku: str) -> InventoryItem | None:
        return self.inventory.get(sku)

    async def get_sale(self, sale_id: str) -> Sale | None:
        return self.sales.get(sale_id)

    async def process_order(
        self, customer_id: str, sku: str, quantity: int, idempotency_key: str
    ) -> Sale:
        async with self._lock:
            if existing := self.idempotency.get(idempotency_key):
                return self.sales[existing]
            if customer_id not in self.customers:
                raise NotFoundError("Customer was not found")
            item = self.inventory.get(sku)
            if item is None:
                raise NotFoundError("Inventory item was not found")
            if item.quantity < quantity:
                raise ConflictError("Insufficient inventory")

            sale = Sale(
                id=f"sale_{uuid4().hex[:12]}",
                customer_id=customer_id,
                sku=sku,
                quantity=quantity,
                total=item.unit_price * quantity,
                status=SaleStatus.CONFIRMED,
                created_at=utc_now(),
            )
            updated = item.model_copy(
                update={"quantity": item.quantity - quantity, "updated_at": utc_now()}
            )
            self.inventory[sku] = updated
            self.sales[sale.id] = sale
            self.idempotency[idempotency_key] = sale.id
            return sale

    async def update_inventory(self, sku: str, quantity_delta: int) -> InventoryItem:
        async with self._lock:
            item = self.inventory.get(sku)
            if item is None:
                raise NotFoundError("Inventory item was not found")
            new_quantity = item.quantity + quantity_delta
            if new_quantity < 0:
                raise ConflictError("Inventory quantity cannot become negative")
            updated = item.model_copy(update={"quantity": new_quantity, "updated_at": utc_now()})
            self.inventory[sku] = updated
            return updated

    async def create_ticket(
        self, customer_id: str, subject: str, description: str, priority: str
    ) -> SupportTicket:
        async with self._lock:
            if customer_id not in self.customers:
                raise NotFoundError("Customer was not found")
            now = utc_now()
            ticket = SupportTicket(
                id=f"ticket_{uuid4().hex[:12]}",
                customer_id=customer_id,
                subject=subject,
                description=description,
                priority=priority,
                status=TicketStatus.OPEN,
                created_at=now,
                updated_at=now,
            )
            self.tickets[ticket.id] = ticket
            return ticket

    async def health(self) -> bool:
        return True

    async def close(self) -> None:
        return None


class PostgresRetailRepository:
    """Production adapter using bounded asyncpg connections and SQL transactions."""

    def __init__(self, pool: PostgresConnectionPool) -> None:
        self.pool = pool

    @staticmethod
    def _model(model: type[Any], record: Any) -> Any:
        return model.model_validate(dict(record)) if record else None

    async def get_customer(self, customer_id: str) -> Customer | None:
        async with self.pool.connection() as connection:
            row = await connection.fetchrow("SELECT * FROM customers WHERE id=$1", customer_id)
        return self._model(Customer, row)

    async def get_inventory(self, sku: str) -> InventoryItem | None:
        async with self.pool.connection() as connection:
            row = await connection.fetchrow("SELECT * FROM inventory WHERE sku=$1", sku)
        return self._model(InventoryItem, row)

    async def get_sale(self, sale_id: str) -> Sale | None:
        async with self.pool.connection() as connection:
            row = await connection.fetchrow("SELECT * FROM sales WHERE id=$1", sale_id)
        return self._model(Sale, row)

    async def process_order(
        self, customer_id: str, sku: str, quantity: int, idempotency_key: str
    ) -> Sale:
        async with self.pool.connection() as connection, connection.transaction():
            existing = await connection.fetchrow(
                "SELECT * FROM sales WHERE idempotency_key=$1", idempotency_key
            )
            if existing:
                return self._model(Sale, existing)
            if not await connection.fetchval("SELECT 1 FROM customers WHERE id=$1", customer_id):
                raise NotFoundError("Customer was not found")
            item = await connection.fetchrow(
                "SELECT * FROM inventory WHERE sku=$1 FOR UPDATE", sku
            )
            if item is None:
                raise NotFoundError("Inventory item was not found")
            if item["quantity"] < quantity:
                raise ConflictError("Insufficient inventory")
            sale_id = f"sale_{uuid4().hex[:12]}"
            total = item["unit_price"] * quantity
            await connection.execute(
                "UPDATE inventory SET quantity=quantity-$1, updated_at=NOW() WHERE sku=$2",
                quantity,
                sku,
            )
            row = await connection.fetchrow(
                """INSERT INTO sales
                   (id, customer_id, sku, quantity, total, status, idempotency_key)
                   VALUES ($1,$2,$3,$4,$5,'confirmed',$6) RETURNING *""",
                sale_id,
                customer_id,
                sku,
                quantity,
                total,
                idempotency_key,
            )
            return self._model(Sale, row)

    async def update_inventory(self, sku: str, quantity_delta: int) -> InventoryItem:
        async with self.pool.connection() as connection, connection.transaction():
            item = await connection.fetchrow(
                "SELECT * FROM inventory WHERE sku=$1 FOR UPDATE", sku
            )
            if item is None:
                raise NotFoundError("Inventory item was not found")
            if item["quantity"] + quantity_delta < 0:
                raise ConflictError("Inventory quantity cannot become negative")
            row = await connection.fetchrow(
                """UPDATE inventory SET quantity=quantity+$1, updated_at=NOW()
                   WHERE sku=$2 RETURNING *""",
                quantity_delta,
                sku,
            )
            return self._model(InventoryItem, row)

    async def create_ticket(
        self, customer_id: str, subject: str, description: str, priority: str
    ) -> SupportTicket:
        async with self.pool.connection() as connection:
            if not await connection.fetchval("SELECT 1 FROM customers WHERE id=$1", customer_id):
                raise NotFoundError("Customer was not found")
            row = await connection.fetchrow(
                """INSERT INTO support_tickets
                   (id,customer_id,subject,description,priority,status)
                   VALUES ($1,$2,$3,$4,$5,'open') RETURNING *""",
                f"ticket_{uuid4().hex[:12]}",
                customer_id,
                subject,
                description,
                priority,
            )
            return self._model(SupportTicket, row)

    async def health(self) -> bool:
        return await self.pool.health()

    async def close(self) -> None:
        await self.pool.close()

