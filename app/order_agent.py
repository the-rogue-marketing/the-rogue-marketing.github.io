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
