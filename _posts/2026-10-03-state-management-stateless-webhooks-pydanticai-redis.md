---
layout: post
title: 'State Management in Stateless Webhooks: Building an Autonomous WhatsApp Commerce Agent with Redis & PydanticAI'
description: Master conversational state persistence across autoscaled stateless webhooks. Learn distributed Redis locks, HMAC payload verification, message history compaction, and PydanticAI dependency injection.
author: professor-xai
categories: [AI Agents & Autonomous Systems]
image: assets/images/conversational-commerce.webp
featured: true
last_modified_at: 2026-10-03
keywords: whatsapp bot state management, pydanticai redis session store, stateless webhook ai agent, conversational commerce python, redis distributed lock python, meta webhook signature verification
faq:
- question: 'Why do serverless webhooks break conversational AI agent state?'
  answer: 'Webhook platforms (Meta WhatsApp, Twilio, Stripe) send independent HTTP POST requests per incoming event. In autoscaled environments (AWS ECS Fargate, Kubernetes, or Cloud Run), two successive messages from the same user land on different ephemeral containers with zero shared in-memory state.'
- question: 'How do you prevent race conditions when a user sends multiple messages rapidly?'
  answer: 'Use Redis distributed locking via atomic "SET key value NX PX <milliseconds>". If a second webhook arrives while the agent is still generating the response for the first message, the lock forces the second request to either queue or cleanly append to the prompt context rather than overwriting state.'
- question: 'How do you verify the authenticity of WhatsApp webhook payloads in FastAPI?'
  answer: 'Compute the HMAC-SHA256 signature of the raw request payload using your Meta App Secret and compare it to the "X-Hub-Signature-256" HTTP header using constant-time comparison (hmac.compare_digest).'
tags: [AI Agents, PydanticAI, Python, DevOps, Redis]
---

When deploying conversational AI commerce agents on platforms like **WhatsApp Business Cloud API**, **Telegram**, or **Twilio SMS**, your application backend receives isolated, asynchronous HTTP POST webhook events.

In modern containerized cloud architectures (AWS ECS, Google Cloud Run, Kubernetes), two successive messages from the same customer will almost certainly be routed to **completely different container instances**.

Without a centralized, race-condition-resistant state layer:
* The agent suffers from **amnesia**: forgetting what product the customer asked for two seconds earlier.
* **Race conditions corrupt data**: when a customer sends two messages in rapid succession (*"Add 2 shirts"* followed immediately by *"Actually make that blue"*), two parallel webhook handlers execute concurrently, causing duplicate charges or shopping cart overwrite bugs.

In this guide, we engineer a **production-ready state management architecture** for stateless webhooks using **FastAPI**, **Redis distributed locks**, and **PydanticAI typed dependency injection**.

---

## 1. Architectural Blueprint: The Stateless Webhook Loop

```
                         Meta WhatsApp Cloud Servers
                                     │
                 ┌───────────────────┴───────────────────┐
                 │ HTTP POST Webhook                     │ HTTP POST Webhook
                 │ Message 1: "Add 2 shirts"             │ Message 2: "Make it blue"
                 ▼                                       ▼
    ┌───────────────────────────┐           ┌───────────────────────────┐
    │ Container A (AWS Fargate) │           │ Container B (AWS Fargate) │
    └─────────────┬─────────────┘           └─────────────┬─────────────┘
                  │                                       │
                  ▼                                       ▼
    ┌───────────────────────────────────────────────────────────────────┐
    │ Redis Central State & Mutex Layer                                 │
    │ 1. Atomic Distributed Lock: SET lock:user:phone NX PX 15000       │
    │    Container A gets Lock; Container B waits or queues             │
    │ 2. Session Hydration: GET session:user:phone                      │
    │    Retrieves Active Cart, Lead Stage & Recent Message History     │
    └─────────────────────────────────┬─────────────────────────────────┘
                                      │
                                      ▼
    ┌───────────────────────────────────────────────────────────────────┐
    │ PydanticAI Agent Turn                                             │
    │ Injects session via RunContext[CustomerSession]                   │
    │ Executes type-safe tools: add_to_cart(), check_stock()            │
    └─────────────────────────────────┬─────────────────────────────────┘
                                      │
                                      ▼
    ┌───────────────────────────────────────────────────────────────────┐
    │ State Persistence & Outbound Dispatch                             │
    │ 1. Saves updated cart & message history to Redis (24h TTL)        │
    │ 2. Releases Redis Distributed Lock                                │
    │ 3. Dispatches WhatsApp response via Meta Graph API                │
    └───────────────────────────────────────────────────────────────────┘
```

---

## 2. Cryptographic Webhook Security & Meta HMAC Verification

Before processing any webhook payload, verify that the request genuinely originated from Meta servers using **HMAC SHA-256**:

```python
import hmac
import hashlib
import os
from fastapi import HTTPException, status

META_APP_SECRET = os.environ.get("META_APP_SECRET", "super-secret-app-token").encode("utf-8")

def verify_meta_webhook_signature(raw_body_bytes: bytes, signature_header: str | None):
    """Guarantees the webhook payload was signed by Meta's private secret."""
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header"
        )
    
    # Expected format: sha256=<hex_digest>
    try:
        hash_algorithm, received_signature = signature_header.split("=")
        if hash_algorithm != "sha256":
            raise ValueError()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid signature header format")

    computed_signature = hmac.new(META_APP_SECRET, raw_body_bytes, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(computed_signature, received_signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HMAC signature verification failed"
        )
```

---

## 3. Redis Distributed Mutex Context Manager

To prevent race conditions when users send multiple messages within milliseconds of each other, we implement an asynchronous Redis lock using atomic `SET NX PX`:

```python
import asyncio
import redis.asyncio as aioredis
from contextlib import asynccontextmanager

@asynccontextmanager
async def distributed_user_lock(
    redis_client: aioredis.Redis,
    user_id: str,
    timeout_ms: int = 15000,
    retry_delay_sec: float = 0.25,
    max_retries: int = 20
):
    """
    Acquires an atomic distributed lock for a user phone number.
    Ensures sequential processing of conversational turns.
    """
    lock_key = f"lock:user:{user_id}"
    token = f"{user_id}:{asyncio.get_event_loop().time()}"
    acquired = False

    for attempt in range(max_retries):
        # Atomic lock acquisition: Set if Not Exists with Expiry in milliseconds
        res = await redis_client.set(lock_key, token, nx=True, px=timeout_ms)
        if res:
            acquired = True
            break
        await asyncio.sleep(retry_delay_sec)

    if not acquired:
        raise TimeoutError(f"Could not acquire distributed lock for user {user_id}. Request concurrent.")

    try:
        yield
    finally:
        # Atomic release via Lua script (verifies token ownership before deleting)
        release_lua = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        await redis_client.eval(release_lua, 1, lock_key, token)
```

---

## 4. The Complete Commerce Agent & Webhook Implementation

Below is the complete FastAPI webhook application that manages shopping cart state and conversation history:

```python
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from fastapi import FastAPI, Request, Header
import json

class CartLineItem(BaseModel):
    sku: str
    item_name: str
    quantity: int
    unit_price: float

class CustomerCommerceSession(BaseModel):
    phone_number: str
    cart_items: List[CartLineItem] = Field(default_factory=list)
    shipping_address: Optional[str] = None
    conversation_summary: str = ""

# Initialize Agent with typed CustomerCommerceSession dependencies
commerce_agent = Agent(
    "google-gla:gemini-2.5-flash",
    deps_type=CustomerCommerceSession,
    system_prompt="""
You are an executive shopping assistant for Acme Apparel on WhatsApp.
Help users discover catalog items, configure sizing/colors, add items to their cart, and confirm orders.
Keep messages concise (under 250 characters per response) for mobile messaging readability.
"""
)

@commerce_agent.tool
def add_product_to_cart(
    ctx: RunContext[CustomerCommerceSession],
    sku: str,
    product_name: str,
    quantity: int,
    price: float
) -> str:
    """Adds a validated item to the customer's active shopping cart."""
    # Check if item already in cart; increment if so
    for item in ctx.deps.cart_items:
        if item.sku == sku:
            item.quantity += quantity
            return f"Updated: {item.quantity}x {product_name} in cart."
            
    ctx.deps.cart_items.append(CartLineItem(
        sku=sku,
        item_name=product_name,
        quantity=quantity,
        unit_price=price
    ))
    return f"Added {quantity}x {product_name} to cart. Total items: {len(ctx.deps.cart_items)}."

@commerce_agent.tool
def get_current_cart(ctx: RunContext[CustomerCommerceSession]) -> str:
    """Returns the itemized list and total price of items currently in the cart."""
    if not ctx.deps.cart_items:
        return "Your cart is currently empty."
        
    lines = [f"- {i.quantity}x {i.item_name} (${i.unit_price * i.quantity:.2f})" for i in ctx.deps.cart_items]
    total = sum(i.unit_price * i.quantity for i in ctx.deps.cart_items)
    return f"Current Cart:\n" + "\n".join(lines) + f"\nTotal: ${total:.2f}"

app = FastAPI()
r = aioredis.from_url("redis://localhost:6379", decode_responses=False)

@app.post("/webhook/whatsapp")
async def whatsapp_webhook_handler(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None)
):
    # 1. Read raw body and verify Meta cryptographic signature
    raw_body = await request.body()
    verify_meta_webhook_signature(raw_body, x_hub_signature_256)

    # 2. Extract message metadata from Meta Graph payload
    payload = json.loads(raw_body.decode("utf-8"))
    
    try:
        msg_entry = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        customer_phone = msg_entry["from"]
        user_text = msg_entry["text"]["body"]
    except (KeyError, IndexError):
        # Ignore delivery status receipts and read-pings
        return {"status": "ignored"}

    # 3. Process turn inside Redis Distributed Lock
    async with distributed_user_lock(r, customer_phone):
        session_key = f"session:whatsapp:{customer_phone}"
        
        # Hydrate session from Redis
        raw_session_bytes = await r.get(session_key)
        if raw_session_bytes:
            session = CustomerCommerceSession.model_validate_json(raw_session_bytes.decode("utf-8"))
        else:
            session = CustomerCommerceSession(phone_number=customer_phone)

        # Execute Agent Turn with hydrated session context
        result = await commerce_agent.run(user_text, deps=session)

        # Persist updated session state back to Redis with 24-hour expiration
        await r.set(session_key, session.model_dump_json().encode("utf-8"), ex=86400)

        # 4. In production: Dispatch reply via WhatsApp Graph API
        print(f"\n📱 WhatsApp Reply to {customer_phone}: {result.data}")
        # dispatch_whatsapp_message(customer_phone, result.data)

    return {"status": "success"}
```

---

## 5. Production Takeaways & Best Practices

1. **Always Verify HMAC Signatures**: Failing to verify signatures leaves your webhook vulnerable to forged requests that drain LLM API tokens.
2. **Use Constant-Time Comparison**: Always use `hmac.compare_digest` to prevent timing attacks against your signature headers.
3. **Set 24-Hour TTLs on Sessions**: WhatsApp Business defines a 24-hour customer service messaging window. Expiring session hashes after 24 hours cleans up inactive Redis memory automatically.
4. **Idempotency Keys for Side-Effects**: When processing payment checkouts or Stripe checkout URLs, use the WhatsApp `message_id` as an idempotency key to prevent accidental duplicate charges.
