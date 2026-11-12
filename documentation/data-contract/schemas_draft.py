"""
DRAFT data contract: what the AI passes to the backend  (Floyd = backend, Marija = AI).
Single source of truth. When both agree, this file moves to Application/V3/backend/schemas.py.

Design rules (proposal - discuss them in the agreement meeting):
  R1. The AI NEVER sends Odoo IDs, Odoo model names, Odoo field names (partner_id, move_type...) or taxes.
      It sends what the USER said (customer_name, product_name, quantity). The backend maps to Odoo.
  R2. The AI picks exactly ONE action per message from a small closed list.
  R3. Every field the backend needs must be optional-or-missing-handled: if the user did not say it,
      the AI leaves it out (null) and the backend asks the user - the AI must not guess.
  R4. The backend never trusts a number from the AI for money: unit_price is optional and, if given,
      is only accepted as an explicit user override (flagged for approval).
  R5. schema_version lets us change the contract without silent breakage.

Use with Ollama structured output:   ollama.chat(..., format=AIAction.model_json_schema())
"""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "0.1"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown keys from the AI = validation error, not silently ignored


class Line(_Strict):
    product_name: str = Field(min_length=1, description="Product exactly as the user wrote it, e.g. 'Chair'")
    quantity: float = Field(gt=0, description="Number of units, must be > 0")
    unit_price: Optional[float] = Field(
        default=None, ge=0,
        description="ONLY if the user explicitly stated a price. Otherwise null - the backend uses Odoo's price.")


class CreateInvoice(_Strict):
    action: Literal["create_invoice"]
    customer_name: str = Field(min_length=1, description="Customer as the user wrote it, e.g. 'Pepsi'")
    lines: list[Line] = Field(min_length=1)
    invoice_date: Optional[date] = Field(default=None, description="ISO date YYYY-MM-DD; null = today")
    from_order: Optional[str] = Field(default=None, description="Sales order reference like 'S00001' if the user names one")
    source_text: Optional[str] = Field(default=None, description="The part of the user message this came from (for the audit log)")


class CreateSalesOrder(_Strict):
    action: Literal["create_sales_order"]
    customer_name: str = Field(min_length=1)
    lines: list[Line] = Field(min_length=1)
    source_text: Optional[str] = None


class Lookup(_Strict):
    """Read-only questions. The AI chooses a named query - NOT a free Odoo model/domain."""
    action: Literal["lookup"]
    what: Literal["customers", "products", "sales_orders", "invoices"]
    search_text: Optional[str] = Field(default=None, description="Name/reference fragment to search for")
    limit: int = Field(default=10, ge=1, le=50)


class AskClarification(_Strict):
    """The AI needs information from the user before anything can be prepared."""
    action: Literal["ask_clarification"]
    missing: list[Literal["customer", "product", "quantity", "date", "other"]] = Field(min_length=1)
    question: str = Field(min_length=1, description="One short question to the user")


class Refuse(_Strict):
    """Request is outside what the system does (e.g. delete, change prices, read system data)."""
    action: Literal["refuse"]
    reason: str


AIAction = Annotated[
    Union[CreateInvoice, CreateSalesOrder, Lookup, AskClarification, Refuse],
    Field(discriminator="action"),
]


class AIEnvelope(_Strict):
    schema_version: Literal["0.1"] = "0.1"
    result: AIAction


# ---------------------------------------------------------------------------
# Backend -> UI / AI replies (so Marija's UI and Floyd's validators speak the same language)
# ---------------------------------------------------------------------------
class Candidate(_Strict):
    id: int
    name: str


class Warning_(_Strict):
    code: Literal["PRICE_OVERRIDE", "DUPLICATE_SUSPECTED", "AMBIGUOUS_MATCH", "TAX_DEFAULTED", "ORDER_ALREADY_INVOICED"]
    message: str


class NeedsApproval(_Strict):
    status: Literal["needs_approval"]
    action_id: str                                 # pending action stored on the backend (expires)
    expires_in_seconds: int
    summary: str
    customer: Candidate
    lines: list[dict]                              # resolved lines: product, qty, unit_price, subtotal
    totals: dict                                   # untaxed, tax, total (from Odoo, not from the AI)
    warnings: list[Warning_] = []


class NeedsClarification(_Strict):
    status: Literal["needs_clarification"]
    field: Literal["customer", "product", "quantity", "date"]
    reason: Literal["AMBIGUOUS", "NOT_FOUND", "MISSING"]
    candidates: list[Candidate] = []               # e.g. 'Pepsi' vs 'Pepsi Cola Bottling'
    question: str


class Rejected(_Strict):
    status: Literal["rejected"]
    code: Literal["VALIDATION_ERROR", "NOT_ALLOWED", "DUPLICATE", "EXPIRED", "ODOO_ERROR"]
    message: str


class Created(_Strict):
    status: Literal["created"]
    odoo_model: str
    odoo_id: int
    odoo_name: Optional[str] = None                # e.g. 'S00001' / 'INV/2026/00001' (draft invoices have none yet)
    state: Literal["draft"]
