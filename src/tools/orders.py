from datetime import datetime, date
from typing import Optional, Dict, Any, Callable
from src.utils.loader import get_data_loader, DataLoader
from src.utils.models import Order, OrderStatusResponse, ReturnEligibilityResponse

NON_RETURNABLE_CATEGORIES = {
    "innerwear", "socks", "jewellery", "jewelry",
    "beauty", "fragrance", "face masks", "gift cards"
}

# Generic message used for BOTH "order does not exist" and "order exists but
# belongs to someone else". Using one message for both cases prevents an
# attacker from using order-ID enumeration to discover which order IDs are
# valid for other customers (see _authorize_order below).
_NOT_FOUND_MESSAGE = (
    "Order '{order_id}' was not found on this account. Please double-check the "
    "order ID, or make sure you're signed in with the email the order was placed under."
)


def _today() -> date:
    """Current date used for return-window math. Kept as a function (rather than a
    hardcoded constant) so it always reflects real time instead of silently drifting
    out of date."""
    return date.today()


def _authorize_order(loader: DataLoader, order: Order, requester_email: str) -> bool:
    """
    Confirms `order` actually belongs to the authenticated requester.
    This is the enforcement point for Policy Section 7 / prompt rule #4
    ("never discuss orders belonging to a different customer") -- it does NOT
    rely on the LLM remembering to check this itself.
    """
    if not requester_email:
        return False
    owner = loader.get_customer_by_id(order.customer_id)
    if not owner:
        return False
    return owner.email.strip().lower() == requester_email.strip().lower()


def _get_order_status_impl(order_id: str, requester_email: str) -> Dict[str, Any]:
    loader = get_data_loader()
    order = loader.get_order_by_id(order_id)

    if not order or not _authorize_order(loader, order, requester_email):
        return OrderStatusResponse(
            found=False,
            order_id=order_id,
            message=_NOT_FOUND_MESSAGE.format(order_id=order_id),
        ).model_dump()

    requires_human = False
    delay_credit = False
    msg_suffix = ""

    if order.status == "lost_in_transit":
        requires_human = True
        msg_suffix = " IMPORTANT: Order is marked lost in transit. Per Policy Section 1.6, this must be escalated to a human agent to process a free replacement or refund."
    elif order.status == "delayed":
        delay_credit = True
        msg_suffix = " Note: This shipment is delayed past expected delivery and qualifies for a ₹250 store credit on request (Policy Section 1.5)."
    elif order.status == "cancelled":
        msg_suffix = f" Order was cancelled on {order.cancelled_at}. Refund status: {order.refund_status}."

    items_str = ", ".join([f"{item.name} ({item.sku}, Size: {item.size}, Qty: {item.qty})" for item in order.items])

    return OrderStatusResponse(
        found=True,
        order_id=order.order_id,
        status=order.status,
        carrier=order.carrier,
        tracking_number=order.tracking_number,
        expected_delivery=order.expected_delivery,
        delivered_at=order.delivered_at,
        payment_method=order.payment_method,
        items_summary=items_str,
        delay_credit_eligible=delay_credit,
        requires_human_escalation=requires_human,
        message=f"Order {order.order_id} status is '{order.status}'. Carrier: {order.carrier or 'N/A'}, Tracking: {order.tracking_number or 'N/A'}.{msg_suffix}"
    ).model_dump()


def _check_return_eligibility_impl(order_id: str, sku: str, requester_email: str) -> Dict[str, Any]:
    """
    Evaluates return/exchange eligibility against Trendly's strict policies:
    - 30-day window from delivery date
    - Category exclusions (innerwear, jewellery, etc.)
    - Final sale rules (size exchange only)
    - Lost / Cancelled order rules
    """
    loader = get_data_loader()
    order = loader.get_order_by_id(order_id)

    if not order or not _authorize_order(loader, order, requester_email):
        return ReturnEligibilityResponse(
            eligible=False,
            order_id=order_id,
            sku=sku,
            action_allowed="none",
            reason=_NOT_FOUND_MESSAGE.format(order_id=order_id),
        ).model_dump()

    target_item = next((item for item in order.items if item.sku.upper() == sku.upper()), None)
    if not target_item:
        return ReturnEligibilityResponse(
            eligible=False,
            order_id=order_id,
            sku=sku,
            action_allowed="none",
            payment_method=order.payment_method,
            reason=f"SKU '{sku}' was not found in Order '{order_id}'."
        ).model_dump()

    if order.status == "cancelled":
        return ReturnEligibilityResponse(
            eligible=False,
            order_id=order_id,
            sku=sku,
            action_allowed="none",
            payment_method=order.payment_method,
            reason="Order has been cancelled. Returns cannot be raised against cancelled orders."
        ).model_dump()

    if order.status == "lost_in_transit":
        return ReturnEligibilityResponse(
            eligible=False,
            order_id=order_id,
            sku=sku,
            action_allowed="escalate_human",
            payment_method=order.payment_method,
            reason="Order is lost in transit. This is handled as a lost-parcel claim by a human agent, not a standard return."
        ).model_dump()

    if order.status != "delivered" or not order.delivered_at:
        return ReturnEligibilityResponse(
            eligible=False,
            order_id=order_id,
            sku=sku,
            action_allowed="none",
            payment_method=order.payment_method,
            reason=f"Order has not been delivered yet (current status: {order.status})."
        ).model_dump()

    delivery_dt = datetime.fromisoformat(order.delivered_at.replace("Z", "+00:00")).date()
    days_since_delivery = (_today() - delivery_dt).days

    if days_since_delivery > 30:
        return ReturnEligibilityResponse(
            eligible=False,
            order_id=order_id,
            sku=sku,
            action_allowed="refused",
            payment_method=order.payment_method,
            days_since_delivery=days_since_delivery,
            reason=f"Item was delivered {days_since_delivery} days ago ({order.delivered_at[:10]}), which exceeds Trendly's strict 30-calendar-day return window."
        ).model_dump()

    if target_item.category.lower() in NON_RETURNABLE_CATEGORIES:
        return ReturnEligibilityResponse(
            eligible=False,
            order_id=order_id,
            sku=sku,
            action_allowed="refused",
            payment_method=order.payment_method,
            days_since_delivery=days_since_delivery,
            reason=f"Items in the '{target_item.category}' category cannot be returned or exchanged for hygiene and safety reasons (Policy Section 2.3)."
        ).model_dump()

    if target_item.final_sale:
        return ReturnEligibilityResponse(
            eligible=True,
            order_id=order_id,
            sku=sku,
            action_allowed="size_exchange_only",
            payment_method=order.payment_method,
            days_since_delivery=days_since_delivery,
            reason=f"Item '{target_item.name}' was marked Final Sale. Per Policy Section 2.4, it is eligible for SIZE EXCHANGE ONLY (no refunds or store credit)."
        ).model_dump()

    return ReturnEligibilityResponse(
        eligible=True,
        order_id=order_id,
        sku=sku,
        action_allowed="full_return",
        payment_method=order.payment_method,
        days_since_delivery=days_since_delivery,
        reason=f"Item '{target_item.name}' is fully eligible for return or size exchange within the 30-day window."
    ).model_dump()


def make_get_order_status_tool(requester_email: str) -> Callable[[str], Dict[str, Any]]:
    """
    Builds a `get_order_status(order_id)` tool bound to a single authenticated
    customer's email. The email is captured in this closure -- NOT exposed as an
    LLM-settable parameter -- so the model can never pass a different customer's
    email to view someone else's order (see Policy Section 7).
    """

    def get_order_status(order_id: str) -> Dict[str, Any]:
        """
        Retrieves status, tracking, delivery details, and policy flags for a Trendly
        order belonging to the currently authenticated customer. Only orders linked
        to this chat session's verified account email can be retrieved.
        """
        return _get_order_status_impl(order_id, requester_email)

    return get_order_status


def make_check_return_eligibility_tool(requester_email: str) -> Callable[[str, str], Dict[str, Any]]:
    """
    Builds a `check_return_eligibility(order_id, sku)` tool bound to a single
    authenticated customer's email, for the same reason as above.
    """

    def check_return_eligibility(order_id: str, sku: str) -> Dict[str, Any]:
        """
        Evaluates return/exchange eligibility against Trendly's strict policies
        (30-day window, category exclusions, final-sale rules, lost/cancelled order
        rules) for an order belonging to the currently authenticated customer.
        """
        return _check_return_eligibility_impl(order_id, sku, requester_email)

    return check_return_eligibility
