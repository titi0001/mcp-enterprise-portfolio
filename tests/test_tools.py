import pytest

from retail_mcp.domain import CreateTicketInput, InventoryUpdateInput, ProcessOrderInput
from retail_mcp.errors import AuthorizationError, ConflictError


async def test_order_is_atomic_and_idempotent(tool_manager, repository, admin) -> None:
    data = ProcessOrderInput(
        customer_id="cus_1001",
        sku="SKU-RED-01",
        quantity=2,
        idempotency_key="checkout-attempt-0001",
    )
    first = await tool_manager.process_order(admin, data)
    second = await tool_manager.process_order(admin, data)
    assert second.id == first.id
    assert repository.inventory["SKU-RED-01"].quantity == 48


async def test_failed_order_does_not_decrement_inventory(tool_manager, repository, admin) -> None:
    before = repository.inventory["SKU-RED-01"].quantity
    data = ProcessOrderInput(
        customer_id="cus_1001",
        sku="SKU-RED-01",
        quantity=100,
        idempotency_key="checkout-attempt-0002",
    )
    with pytest.raises(ConflictError):
        await tool_manager.process_order(admin, data)
    assert repository.inventory["SKU-RED-01"].quantity == before


async def test_inventory_manager_updates_stock(tool_manager, repository, inventory_manager) -> None:
    result = await tool_manager.update_inventory(
        inventory_manager,
        InventoryUpdateInput(sku="SKU-BAG-02", quantity_delta=5, reason="warehouse receipt"),
    )
    assert result.quantity == 30
    assert repository.inventory["SKU-BAG-02"].quantity == 30


async def test_support_cannot_update_inventory(tool_manager, support) -> None:
    with pytest.raises(AuthorizationError):
        await tool_manager.update_inventory(
            support,
            InventoryUpdateInput(sku="SKU-BAG-02", quantity_delta=5, reason="not allowed"),
        )


async def test_support_creates_ticket(tool_manager, support) -> None:
    ticket = await tool_manager.create_ticket(
        support,
        CreateTicketInput(
            customer_id="cus_1001",
            subject="Delivery delay",
            description="The customer has not received the order.",
            priority="high",
        ),
    )
    assert ticket.customer_id == "cus_1001"
    assert ticket.status == "open"

