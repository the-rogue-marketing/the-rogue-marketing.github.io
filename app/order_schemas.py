from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class OrderType(str, Enum):
    DELIVERY = "delivery"
    TAKEOUT = "takeout"


class MenuItem(BaseModel):
    id: str = Field(..., description="Unique product ID code")
    name: str = Field(..., description="Name of the catalog product")
    price: float = Field(..., description="Cost of a single item")
    category: str = Field(..., description="Category (e.g., 'Mains', 'Drinks')")


class CartItem(BaseModel):
    item_id: str = Field(..., description="Mapped menu item ID")
    name: str = Field(..., description="Name of the product")
    quantity: int = Field(..., description="Number of units added to cart")
    price: float = Field(..., description="Price per unit at addition time")


class CartState(BaseModel):
    items: List[CartItem] = Field(default_factory=list, description="List of items currently in the cart")
    order_type: Optional[OrderType] = Field(None, description="Delivery or Takeout preference")
    delivery_address: Optional[str] = Field(None, description="Physical address for delivery orders")
    patient_phone: Optional[str] = Field(None, description="User identifier number")
    is_confirmed: bool = Field(False, description="Checkout confirmation status")
