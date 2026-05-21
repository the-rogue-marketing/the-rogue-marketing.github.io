from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class WebOrderSubmission(BaseModel):
    customer_name: str = Field(..., description="Full name of the purchasing customer")
    phone_number: str = Field(..., description="Phone number formatted with country code (e.g. +123456789)")
    shipping_address: str = Field(..., description="Physical delivery address for shipping")
    product_sku: str = Field(..., description="Stock keeping unit of the purchased item")
    quantity: int = Field(default=1, description="Quantity purchased")
    order_total: float = Field(..., description="Gross payment amount")


class OrderVerificationState(BaseModel):
    order_id: str = Field(..., description="Unique generated transaction identifier")
    customer_name: str = Field(..., description="Name associated with the order")
    phone_number: str = Field(..., description="Target contact number")
    shipping_address: str = Field(..., description="Address to confirm")
    product_sku: str = Field(..., description="Product SKU")
    quantity: int = Field(..., description="Quantity purchased")
    order_total: float = Field(..., description="Order cost")
    is_verified: bool = Field(False, description="Verification status flag")
    custom_delivery_notes: Optional[str] = Field(None, description="Special instructions captured by VLM")
    verification_timestamp: Optional[datetime] = Field(None, description="Time stamp of successful confirmation")
