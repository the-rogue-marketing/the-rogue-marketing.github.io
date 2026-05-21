import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
from pydantic_ai import Agent, RunContext
from app.verify_schemas import OrderVerificationState, WebOrderSubmission

# Persistent Database Emulator
VERIFICATION_DB: Dict[str, OrderVerificationState] = {}


@dataclass
class VerificationDeps:
    """Agent dependencies holding transaction reference databases."""
    db: Dict[str, OrderVerificationState]
    active_phone: str


# Initialize Pydantic AI Verification Agent
verification_agent = Agent(
    model="google-gla:gemini-2.5-flash",
    deps_type=VerificationDeps,
    system_prompt=(
        "You are an automated e-commerce transaction auditor at Rogue Shop. "
        "Your task is to coordinate with the customer on WhatsApp to verify their recent web order. "
        "Strictly adhere to the following workflow:\n"
        "1. Retrieve the patient/customer order details using their phone number.\n"
        "2. Present the shipping address and purchased item, then ask them to confirm if it is correct.\n"
        "3. If they require changes to the shipping address, update the address in the database.\n"
        "4. Ask if they have any specific delivery instructions (e.g., 'Leave at front gate').\n"
        "5. Once they confirm, trigger the verification tool and send a clean confirmation message.\n"
        "Always be polite, direct, and conversational."
    )
)


@verification_agent.tool
def get_order_details(ctx: RunContext[VerificationDeps]) -> Optional[OrderVerificationState]:
    """Retrieve the pending, unverified order details associated with the customer's phone number."""
    # Find matching pending order in database
    for order in ctx.deps.db.values():
        if order.phone_number == ctx.deps.active_phone and not order.is_verified:
            return order
    return None


@verification_agent.tool
def update_shipping_address(ctx: RunContext[VerificationDeps], new_address: str) -> str:
    """Updates the physical shipping address associated with the order if requested by the customer."""
    for order in ctx.deps.db.values():
        if order.phone_number == ctx.deps.active_phone and not order.is_verified:
            order.shipping_address = new_address
            return f"Shipping address successfully updated to: {new_address}"
    return "No active pending order found to update."


@verification_agent.tool
def verify_booking(
    ctx: RunContext[VerificationDeps], 
    delivery_notes: Optional[str] = None
) -> str:
    """
    Flags the pending order as verified and confirmed in the database.
    Captures any special delivery instructions.
    """
    for order in ctx.deps.db.values():
        if order.phone_number == ctx.deps.active_phone and not order.is_verified:
            order.is_verified = True
            order.custom_delivery_notes = delivery_notes
            order.verification_timestamp = datetime.utcnow()
            return f"Order {order.order_id} has been verified and released to shipping."
    return "Verification failed. No pending matching order found."
