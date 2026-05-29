---
layout: post
title: "Automating WhatsApp and Messenger Conversational Commerce with Pydantic AI and Gemini"
date: 2026-05-21
last_modified_at: 2026-05-21
author: professor-xai
categories: [Generative AI, Conversational Commerce, Full-Stack]
image: assets/images/conversational-commerce.webp
description: "A complete developer guide to building a conversational e-commerce and food ordering system for WhatsApp and Messenger using Pydantic AI, Gemini API, and FastAPI webhook architectures."
keywords: "whatsapp ordering bot gemini, conversational commerce pydantic ai, fastapi whatsapp cloud api webhook, ai restaurant booking system python, docker-compose uv python"
---

Conversational commerce has shifted from a novel customer touchpoint to a core transactional engine. Globally, billions of users interact with businesses daily on messaging platforms like WhatsApp and Facebook Messenger. 

Historically, automating these interactions relied on rigid, rule-based chatbot decision trees. If a customer made a typo, deviated from the script, or asked a question out of order (e.g., changing their delivery address mid-checkout), the system collapsed.

By leveraging Google Gemini as a reasoning engine and Pydantic AI as a type-safe agentic framework, we can build a resilient **Conversational Ordering Assistant**. This assistant manages shopping carts, answers catalog questions, calculates taxes and delivery fees, collects addresses, and triggers ordering pipelines dynamically in response to natural conversation.

This tutorial guides you through implementing a production-grade automated conversational ordering system integrated via a FastAPI Webhook architecture.

---

## System Workflow & State Management

Conversational checkouts require maintaining a persistent state (session history, cart items, delivery method, and address) across stateless webhook invocations. Here is the operational architecture:

```
[ Customer (WhatsApp/Messenger) ]
              |
      [ Messaging API ]
              | (Webhook HTTP POST)
      [ FastAPI Webhook ]
              |
   [ Fetch Session Cart State ]
              |
      [ Pydantic AI Agent ] <---> [ Tool: get_menu ]
              |             <---> [ Tool: modify_cart ]
              |             <---> [ Tool: finalize_checkout ]
      [ Update Cart State ]
              |
      [ Dispatch Reply ]
```

---

## Step 1: Defining State & Transaction Schemas

We will define structured Pydantic models to track the cart items, delivery preferences, and final checkout records.

Create `app/order_schemas.py`:

```python
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
```

---

## Step 2: Designing the Pydantic AI Commerce Agent

The agent requires access to menu catalogs, cart mutators, and order dispatch triggers. Pydantic AI injects these via standard `@agent.tool` configurations.

Create `app/order_agent.py`:

```python
import os
from dataclasses import dataclass
from typing import List, Optional
from pydantic_ai import Agent, RunContext
from app.order_schemas import MenuItem, CartItem, CartState, OrderType

# Mock Restaurant Menu
MOCK_MENU = [
    MenuItem(id="m1", name="Signature Beef Burger", price=12.99, category="Mains"),
    MenuItem(id="m2", name="Truffle Parmesan Fries", price=5.49, category="Sides"),
    MenuItem(id="m3", name="Craft Lemonade", price=3.50, category="Drinks"),
    MenuItem(id="m4", name="Classic Margherita Pizza", price=14.99, category="Mains"),
]


@dataclass
class CommerceDeps:
    """Agent dependencies holding transactional database context."""
    menu: List[MenuItem]
    cart: CartState


# Initialize Pydantic AI Commerce Agent
commerce_agent = Agent(
    model="google-gla:gemini-2.5-flash",
    deps_type=CommerceDeps,
    system_prompt=(
        "You are an energetic, precise virtual order intake assistant for Rogue Kitchen. "
        "Your task is to take customer orders for takeout or delivery over WhatsApp. "
        "Strictly adhere to the following workflow:\n"
        "1. Help the user select items from the menu. Recommend items if they ask.\n"
        "2. Add, remove, or modify items in their cart using the provided tool.\n"
        "3. Confirm their order type (takeout or delivery).\n"
        "4. If delivery is selected, request their physical address.\n"
        "5. Once cart, type, and address (if applicable) are captured, calculate the order total "
        "and ask for final confirmation before triggering checkout.\n"
        "Keep your conversational tone warm, simple, and optimized for mobile screens (use spacing)."
    )
)


@commerce_agent.tool
def get_menu(ctx: RunContext[CommerceDeps]) -> List[MenuItem]:
    """Retrieve the active menu catalog containing product names, categories, and prices."""
    return ctx.deps.menu


@commerce_agent.tool
def modify_cart(
    ctx: RunContext[CommerceDeps], 
    item_id: str, 
    quantity: int
) -> str:
    """
    Adds, updates, or removes items in the customer's shopping cart.
    Set quantity to 0 to remove an item.
    """
    menu_item = next((m for m in ctx.deps.menu if m.id == item_id), None)
    if not menu_item:
        return f"Product with ID '{item_id}' not found."

    # Look for item in cart
    cart_item = next((item for item in ctx.deps.cart.items if item.item_id == item_id), None)

    if quantity <= 0:
        if cart_item:
            ctx.deps.cart.items.remove(cart_item)
            return f"Removed {menu_item.name} from your cart."
        return f"{menu_item.name} is not in your cart."

    if cart_item:
        cart_item.quantity = quantity
        return f"Updated {menu_item.name} quantity to {quantity}."
    
    # Add new item
    ctx.deps.cart.items.append(
        CartItem(
            item_id=menu_item.id,
            name=menu_item.name,
            quantity=quantity,
            price=menu_item.price
        )
    )
    return f"Added {quantity}x {menu_item.name} to your cart."


@commerce_agent.tool
def finalize_checkout(
    ctx: RunContext[CommerceDeps], 
    order_type: OrderType, 
    address: Optional[str] = None
) -> str:
    """
    Validates checkout inputs, updates order type, captures the address, 
    and returns a summary of the order.
    """
    if len(ctx.deps.cart.items) == 0:
        return "Your cart is empty. Please add items before checking out."

    ctx.deps.cart.order_type = order_type
    
    if order_type == OrderType.DELIVERY:
        if not address:
            return "Please provide a physical delivery address to complete your order."
        ctx.deps.cart.delivery_address = address

    # Calculate total pricing
    subtotal = sum(item.price * item.quantity for item in ctx.deps.cart.items)
    delivery_fee = 3.99 if order_type == OrderType.DELIVERY else 0.00
    tax = subtotal * 0.08
    total = subtotal + tax + delivery_fee

    ctx.deps.cart.is_confirmed = True

    # Build response summary
    summary = (
        f"Order Type: {order_type.value.upper()}\n"
        f"Delivery Address: {address or 'N/A'}\n\n"
        "Items:\n"
    )
    for item in ctx.deps.cart.items:
        summary += f"- {item.quantity}x {item.name} (${item.price * item.quantity:.2f})\n"
    
    summary += (
        f"\nSubtotal: ${subtotal:.2f}\n"
        f"Tax (8%): ${tax:.2f}\n"
        f"Delivery Fee: ${delivery_fee:.2f}\n"
        f"Grand Total: ${total:.2f}\n\n"
        "Should I submit this order for preparation?"
    )
    return summary
```

---

## Step 3: FastAPI Webhook & State Pipeline

WhatsApp and Messenger Cloud APIs communicate via standardized HTTP webhooks. When a customer sends a message, the platform delivers a JSON payload. We must parse this payload, load the user's cart state, invoke the Pydantic AI agent, and reply.

Create `app/order_main.py`:

```python
import os
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Dict, Any, List

from app.order_schemas import CartState, MenuItem
from app.order_agent import commerce_agent, CommerceDeps, MOCK_MENU

app = FastAPI(
    title="Rogue Commerce Webhook API",
    version="1.0.0"
)

# Persistent In-Memory Session Storage
# In production, use Redis with a TTL of 24 hours.
SESSION_STORAGE: Dict[str, CartState] = {}


class WebhookPayload(BaseModel):
    """Shorthand schema for incoming messaging payloads."""
    sender_id: str
    message_text: str


def get_or_create_session(sender_id: str) -> CartState:
    if sender_id not in SESSION_STORAGE:
        SESSION_STORAGE[sender_id] = CartState(patient_phone=sender_id)
    return SESSION_STORAGE[sender_id]


@app.post("/webhooks/messaging")
async def handle_incoming_message(payload: WebhookPayload):
    """
    Unified webhook endpoint for WhatsApp and Messenger channels.
    Fetches patient session context, executes agentic reasoning,
    and returns conversational responses.
    """
    try:
        # Load user session
        user_state = get_or_create_session(payload.sender_id)
        
        # Inject context dependency
        deps = CommerceDeps(
            menu=MOCK_MENU,
            cart=user_state
        )

        # Run agent loop asynchronously
        result = await commerce_agent.run(
            payload.message_text,
            deps=deps
        )

        # In production, transmit this text response back using WhatsApp Cloud API:
        # requests.post("https://graph.facebook.com/v18.0/me/messages", json={...})

        return {
            "recipient_id": payload.sender_id,
            "response_text": result.data,
            "session_state": user_state.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook system error: {str(e)}")


@app.get("/webhooks/messaging")
async def verify_webhook(request: Request):
    """Subscription verification endpoint required by Meta Platforms."""
    params = request.query_params
    verify_token = os.getenv("META_VERIFY_TOKEN", "my_secret_token")
    
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == verify_token:
        return Response(content=params.get("hub.challenge"), media_type="text/plain")
    return Response(content="Verification failed", status_code=403)
```

---

## Step 4: Local Testing via Curl

Test the endpoint locally using `curl` to simulate an active user order lifecycle.

### 1. Request Menu Catalog
```bash
curl -X POST http://localhost:8000/webhooks/messaging \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "wa-user-0824",
    "message_text": "Hi, what is on the menu today?"
  }' | python -m json.tool
```

**Example Agent Output Response:**
```json
{
  "recipient_id": "wa-user-0824",
  "response_text": "Hello! Welcome to Rogue Kitchen. Here is what we are serving:\n\n* Mains:\n  - Signature Beef Burger ($12.99)\n  - Classic Margherita Pizza ($14.99)\n* Sides:\n  - Truffle Parmesan Fries ($5.49)\n* Drinks:\n  - Craft Lemonade ($3.50)\n\nWhat can I add to your order today?",
  "session_state": {
    "items": [],
    "order_type": null,
    "delivery_address": null,
    "patient_phone": "wa-user-0824",
    "is_confirmed": false
  }
}
```

### 2. Add Item to Cart
```bash
curl -X POST http://localhost:8000/webhooks/messaging \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "wa-user-0824",
    "message_text": "Add a Signature Beef Burger and Truffle Fries please."
  }' | python -m json.tool
```

**Example Agent Output Response:**
```json
{
  "recipient_id": "wa-user-0824",
  "response_text": "I've added 1x Signature Beef Burger and 1x Truffle Parmesan Fries to your cart.\n\nWould you like this for delivery or takeout?",
  "session_state": {
    "items": [
      { "item_id": "m1", "name": "Signature Beef Burger", "quantity": 1, "price": 12.99 },
      { "item_id": "m2", "name": "Truffle Parmesan Fries", "quantity": 1, "price": 5.49 }
    ],
    "order_type": null,
    "delivery_address": null,
    "patient_phone": "wa-user-0824",
    "is_confirmed": false
  }
}
```

### 3. Coordinate Checkout
```bash
curl -X POST http://localhost:8000/webhooks/messaging \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "wa-user-0824",
    "message_text": "Delivery to 124 Main Street please."
  }' | python -m json.tool
```

**Example Agent Output Response:**
```json
{
  "recipient_id": "wa-user-0824",
  "response_text": "Perfect! Here is your order summary for delivery:\n\nOrder Type: DELIVERY\nDelivery Address: 124 Main Street\n\nItems:\n- 1x Signature Beef Burger ($12.99)\n- 1x Truffle Parmesan Fries ($5.49)\n\nSubtotal: $18.48\nTax (8%): $1.48\nDelivery Fee: $3.99\nGrand Total: $23.95\n\nShould I submit this order for preparation?",
  "session_state": {
    "items": [
      { "item_id": "m1", "name": "Signature Beef Burger", "quantity": 1, "price": 12.99 },
      { "item_id": "m2", "name": "Truffle Parmesan Fries", "quantity": 1, "price": 5.49 }
    ],
    "order_type": "delivery",
    "delivery_address": "124 Main Street",
    "patient_phone": "wa-user-0824",
    "is_confirmed": true
  }
}
```

---

## Conclusion

Transitioning messaging checkouts from legacy rule-based chatbots to Pydantic AI agents reduces cart abandonment and optimizes operational speed. The agent handles natural conversation seamlessly, while Pydantic schemas validate that downstream transactional payloads (like order lines and addresses) remain structurally correct.
