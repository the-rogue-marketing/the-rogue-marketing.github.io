from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


# ----------------------------------------------------
# Pipeline 1: Generic Extraction Schemas
# ----------------------------------------------------
class InvoiceLineItem(BaseModel):
    description: str = Field(..., description="Description of the item or service rendered")
    quantity: Optional[float] = Field(None, description="Quantity of items purchased")
    unit_price: Optional[float] = Field(None, description="Price per unit of the item")
    amount: Optional[float] = Field(None, description="Total amount for this line item")


class GenericInvoiceData(BaseModel):
    vendor_name: str = Field(..., description="Name of the company or vendor issuing the invoice")
    vendor_address: Optional[str] = Field(None, description="Physical or email address of the vendor")
    invoice_number: Optional[str] = Field(None, description="Invoice or receipt identification number")
    invoice_date: Optional[str] = Field(None, description="Date of invoice issuance (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Payment due date (YYYY-MM-DD)")
    subtotal: Optional[float] = Field(None, description="Invoice subtotal before taxes and shipping")
    tax_amount: Optional[float] = Field(None, description="Tax amount listed on the invoice")
    total_amount: float = Field(..., description="Total gross amount payable on the invoice")
    currency: str = Field("USD", description="Currency symbol or standard code")
    line_items: List[InvoiceLineItem] = Field(default_factory=list, description="List of items extracted")


# ----------------------------------------------------
# Pipeline 2: Query-Driven Custom Schemas
# ----------------------------------------------------
class CustomField(BaseModel):
    field_key: str = Field(..., description="Name of the custom field requested (e.g., 'vat_number')")
    extracted_value: Optional[str] = Field(None, description="Value extracted by the agent matching custom prompt")
    confidence_score: float = Field(..., description="Confidence rating between 0.0 and 1.0")


class DynamicInvoiceResponse(BaseModel):
    custom_extractions: List[CustomField] = Field(default_factory=list, description="List of custom requested fields")
