from decimal import Decimal

import pytest

from retail_mcp.domain import InventoryItem, utc_now
from retail_mcp.errors import AuthorizationError, NotFoundError


async def test_support_reads_full_customer(resource_manager, support) -> None:
    customer = await resource_manager.customer(support, "cus_1001")
    assert customer.email == "ana.silva@example.com"


async def test_analyst_receives_masked_customer_pii(resource_manager, analyst) -> None:
    customer = await resource_manager.customer(analyst, "cus_1001")
    assert customer.email == "a***@example.com"


async def test_cache_prevents_stale_backend_read(resource_manager, repository, support) -> None:
    first = await resource_manager.inventory(support, "SKU-RED-01")
    repository.inventory["SKU-RED-01"] = InventoryItem(
        sku="SKU-RED-01",
        name="Changed backend name",
        quantity=1,
        reorder_level=1,
        unit_price=Decimal("1.00"),
        updated_at=utc_now(),
    )
    second = await resource_manager.inventory(support, "SKU-RED-01")
    assert second == first


async def test_missing_resource_has_safe_error(resource_manager, support) -> None:
    with pytest.raises(NotFoundError, match="not found"):
        await resource_manager.customer(support, "cus_missing")


async def test_role_cannot_read_sales(resource_manager, support) -> None:
    with pytest.raises(AuthorizationError):
        await resource_manager.sale(support, "sale_missing")

