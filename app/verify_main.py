import os
import uuid
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any

from app.verify_schemas import WebOrderSubmission, OrderVerificationState
from app.verify_agent import verification_agent, VerificationDeps, VERIFICATION_DB

app = FastAPI(
    title="Form-to-WhatsApp Verification Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class InboundMessagePayload(BaseModel):
    phone_number: str
    message_text: str


@app.post("/api/orders/submit")
async def submit_order_form(submission: WebOrderSubmission):
    """
    Receives e-commerce checkout form submissions.
    Saves unverified order record, then simulates outbound WhatsApp dispatch.
    """
    try:
        order_id = f"RQ-{uuid.uuid4().hex[:6].upper()}"
        
        # Save unverified transaction to database
        new_order = OrderVerificationState(
            order_id=order_id,
            customer_name=submission.customer_name,
            phone_number=submission.phone_number,
            shipping_address=submission.shipping_address,
            product_sku=submission.product_sku,
            quantity=submission.quantity,
            order_total=submission.order_total
        )
        
        VERIFICATION_DB[order_id] = new_order

        # Outbound notification trigger
        # In production, dispatch Meta WhatsApp Template:
        # requests.post("https://graph.facebook.com/v18.0/me/messages", json={...})
        
        outbound_alert = (
            f"Hi {submission.customer_name}, thank you for your order at Rogue Shop!\n"
            f"Please reply to this message to verify your delivery address: {submission.shipping_address}."
        )

        return {
            "status": "pending_verification",
            "order_id": order_id,
            "simulated_whatsapp_outbound": outbound_alert
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/whatsapp")
async def handle_whatsapp_inbound(payload: InboundMessagePayload):
    """
    Receives incoming WhatsApp conversational message replies.
    Restores contextual database loops and updates state.
    """
    try:
        # Load agent context
        deps = VerificationDeps(
            db=VERIFICATION_DB,
            active_phone=payload.phone_number
        )

        # Run agent loop asynchronously
        result = await verification_agent.run(
            payload.message_text,
            deps=deps
        )

        # Retrieve current state of all database records
        db_dump = [order.model_dump() for order in VERIFICATION_DB.values()]

        return {
            "phone_number": payload.phone_number,
            "agent_reply": result.data,
            "verification_database": db_dump
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook execution failure: {str(e)}")


@app.get("/api/orders", response_model=List[OrderVerificationState])
async def get_all_orders():
    """Retrieve catalog of all orders to verify state updates."""
    return list(VERIFICATION_DB.values())


# Mount client pages
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def read_root():
    return FileResponse("app/static/form.html")
