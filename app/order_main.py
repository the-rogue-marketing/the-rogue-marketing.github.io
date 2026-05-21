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
