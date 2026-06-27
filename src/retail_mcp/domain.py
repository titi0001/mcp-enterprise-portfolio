"""Retail domain models exposed through MCP resources and tools."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class CustomerTier(StrEnum):
    STANDARD = "standard"
    GOLD = "gold"
    PLATINUM = "platinum"


class SaleStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class Customer(BaseModel):
    id: str
    name: str
    email: str
    tier: CustomerTier
    region: str
    created_at: datetime


class CustomerView(BaseModel):
    id: str
    name: str
    email: str
    tier: CustomerTier
    region: str


class InventoryItem(BaseModel):
    sku: str
    name: str
    quantity: int = Field(ge=0)
    reorder_level: int = Field(ge=0)
    unit_price: Decimal = Field(gt=0, decimal_places=2)
    updated_at: datetime


class Sale(BaseModel):
    id: str
    customer_id: str
    sku: str
    quantity: int = Field(gt=0)
    total: Decimal = Field(gt=0, decimal_places=2)
    status: SaleStatus
    created_at: datetime


class SupportTicket(BaseModel):
    id: str
    customer_id: str
    subject: str
    description: str
    priority: str
    status: TicketStatus
    created_at: datetime
    updated_at: datetime


class ProcessOrderInput(BaseModel):
    customer_id: str = Field(pattern=r"^cus_[A-Za-z0-9_-]+$")
    sku: str = Field(pattern=r"^[A-Z0-9_-]{3,32}$")
    quantity: int = Field(gt=0, le=100)
    idempotency_key: str = Field(min_length=12, max_length=128)


class InventoryUpdateInput(BaseModel):
    sku: str = Field(pattern=r"^[A-Z0-9_-]{3,32}$")
    quantity_delta: int = Field(ge=-10_000, le=10_000)
    reason: str = Field(min_length=3, max_length=200)


class CreateTicketInput(BaseModel):
    customer_id: str = Field(pattern=r"^cus_[A-Za-z0-9_-]+$")
    subject: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=2_000)
    priority: str = Field(default="normal", pattern=r"^(low|normal|high|critical)$")

    @field_validator("subject", "description")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        cleaned = value.strip()
        if any(ord(char) < 32 and char not in "\n\t" for char in cleaned):
            raise ValueError("control characters are not allowed")
        return cleaned
