---
layout: post
title: 'State Management in Stateless Webhooks: Building an Autonomous WhatsApp Commerce
  Agent with Redis & PydanticAI'
description: How to persist conversational session states in stateless webhook microservices
  using Redis, PostgreSQL, and PydanticAI for WhatsApp & Telegram commerce bots.
author: professor-xai
categories: [AI Agents & Autonomous Systems]
image: assets/images/conversational-commerce.webp
featured: true
last_modified_at: 2026-10-03
keywords: whatsapp bot state management, pydanticai redis session store, stateless
  webhook ai agent, conversational commerce python
faq:
- {question: 'Why do webhooks break traditional AI agent state?', answer: 'Webhook
    platforms (Meta WhatsApp, Twilio, Stripe) send isolated HTTP POST requests per
    message without shared in-memory state across requests in autoscaled cloud environments.'}
- {question: 'How does Redis solve conversational state persistence?', answer: Redis
    stores conversation history and current shopping cart schemas serialized as JSON
    under a fast key (e.g. user_phone_number) with configurable TTL expiration.}
- {question: 'How do you prevent race conditions when users double-tap WhatsApp messages?',
  answer: Use Redis distributed locks (`redlock` or atomic `SETNX`) keyed to the customer
    phone number while the agent processes the active webhook turn.}
tags: [AI Agents, PydanticAI, Python]
---
When building conversational AI assistants for **WhatsApp Business, Telegram, or SMS**, your backend receives individual, isolated HTTP POST webhook payloads. In autoscaling environments (AWS ECS, Google Cloud Run, Kubernetes), two successive messages from the same user often land on entirely different server containers.

Without a robust external state layer, your agent forgets the customer's shopping cart, repeats greeting messages, and hallucinates order details.

Here is the production architecture for implementing **type-safe state persistence with PydanticAI and Redis**.

---

## 1. System Architecture

```
┌─────────────────┐       POST /webhook       ┌───────────────────┐
│ Meta WhatsApp   │ ────────────────────────> │ FastAPI Webhook   │
│ Cloud API       │                           │ Container (Stateless)
└─────────────────┘                           └─────────┬─────────┘
                                                        │
                      ┌─────────────────────────────────┴─────────────────────────────────┐
                      ▼                                                                   ▼
       ┌─────────────────────────────┐                                     ┌─────────────────────────────┐
       │ Redis Session Store         │                                     │ PydanticAI Agent            │
       │ - Message History           │ ─── Injects Context into RunContext ──> │ - Validated Tool Execution  │
       │ - Active Cart & Lead Stage  │                                     │ - Strict Schema Returns     │
       └─────────────────────────────┘                                     └─────────────────────────────┘
```

---

## 2. Complete Python Implementation

```python
import os
import json
import redis.asyncio as redis
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from fastapi import FastAPI, Request

r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

class CartItem(BaseModel):
    sku: str
    quantity: int
    unit_price: float

class CustomerSession(BaseModel):
    phone_number: str
    cart: list[CartItem] = []
    shipping_address: str | None = None

agent = Agent("google-gla:gemini-2.5-flash", deps_type=CustomerSession)

@agent.tool
async def add_item_to_cart(ctx: RunContext[CustomerSession], sku: str, quantity: int) -> str:
    """Adds a validated product SKU and quantity to the customer's cart."""
    ctx.deps.cart.append(CartItem(sku=sku, quantity=quantity, unit_price=29.99))
    return f"Successfully added {quantity}x {sku} to your order. Cart items: {len(ctx.deps.cart)}."

app = FastAPI()

@app.post("/webhook/whatsapp")
async def handle_whatsapp(req: Request):
    payload = await req.json()
    phone = payload["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
    user_text = payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]

    # 1. Hydrate Session from Redis
    raw_session = await r.get(f"session:{phone}")
    if raw_session:
        session = CustomerSession.model_validate_json(raw_session)
    else:
        session = CustomerSession(phone_number=phone)

    # 2. Run Agent Turn with Injected Dependencies
    result = await agent.run(user_text, deps=session)

    # 3. Persist Updated State with 24-hour TTL
    await r.set(f"session:{phone}", session.model_dump_json(), ex=86400)

    # Return response payload to WhatsApp Cloud API
    return {"status": "ok", "reply": result.data}
```

---

## 3. Production Hardening Checklist

- **Distributed Locks**: Enforce 5-second locks per phone number to prevent duplicate charges if users spam clicks.
- **Dead Letter Queues (DLQ)**: If a webhook processing turn fails, route the payload to SQS/RabbitMQ for automated retry rather than dropping user communication.
- **TTL Strategy**: Refresh Redis key expiration on every incoming interaction so active shoppers never lose carts midway.
