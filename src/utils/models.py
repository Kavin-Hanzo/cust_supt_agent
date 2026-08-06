from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Customer(BaseModel):
    customer_id: str
    name: str
    email: str
    phone: str


class OrderItem(BaseModel):
    sku: str = Field(..., description="Unique item SKU")
    name: str = Field(..., description="Display name of the item")
    category: str = Field(..., description="Category: apparel, innerwear, jewellery, footwear, accessories, etc.")
    size: str = Field(..., description="Item size")
    qty: int = Field(1, ge=1, description="Quantity ordered")
    price: float = Field(..., ge=0.0, description="Price per unit in INR")
    final_sale: bool = Field(False, description="Whether item is marked final sale (size exchange only)")
    shipped: Optional[bool] = Field(None, description="Shipment status for partial orders")
    backorder_eta: Optional[str] = Field(None, description="ETA if item is on backorder")


class Order(BaseModel):
    order_id: str = Field(..., description="Order ID (e.g. TR-4521)")
    customer_id: str = Field(..., description="Associated customer ID")
    status: str = Field(..., description="Status: in_transit, delivered, delayed, lost_in_transit, partially_shipped, cancelled")
    placed_at: str = Field(..., description="ISO timestamp when order was placed")
    delivered_at: Optional[str] = Field(None, description="ISO timestamp when delivered")
    expected_delivery: Optional[str] = Field(None, description="Expected delivery date YYYY-MM-DD")
    carrier: Optional[str] = Field(None, description="Carrier name (e.g. BlueDart, Delhivery)")
    tracking_number: Optional[str] = Field(None, description="Tracking AWBN")
    payment_method: str = Field(..., description="Payment method: prepaid_card, credit_card, cash_on_delivery, upi")
    shipping_city: str = Field(..., description="Destination city")
    items: List[OrderItem] = Field(default_factory=list, description="List of items in order")
    total: float = Field(..., ge=0.0, description="Total order amount")
    cancelled_at: Optional[str] = Field(None, description="ISO timestamp if cancelled")
    refund_status: Optional[str] = Field(None, description="Refund status if cancelled")


class OrderStatusResponse(BaseModel):
    found: bool
    order_id: str
    status: Optional[str] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    expected_delivery: Optional[str] = None
    delivered_at: Optional[str] = None
    payment_method: Optional[str] = Field(
        None,
        description="Original payment method (e.g. cash_on_delivery). Needed to detect when a "
                     "refund requires bank details and must be escalated per Policy 3.3.",
    )
    items_summary: Optional[str] = None
    delay_credit_eligible: bool = False
    requires_human_escalation: bool = False
    message: str


class ReturnEligibilityResponse(BaseModel):
    eligible: bool
    order_id: str
    sku: str
    action_allowed: str = Field("none", description="Allowed action: 'full_return', 'size_exchange_only', 'refused', 'escalate_human'")
    reason: str
    payment_method: Optional[str] = Field(
        None,
        description="Original payment method. If 'cash_on_delivery' and a refund (not a size "
                     "exchange) is due, escalate_to_human must be called per Policy 3.3.",
    )
    days_since_delivery: Optional[int] = None
    return_window_days: int = 30


class HandoffPayload(BaseModel):
    triggered: bool = True
    reason: str = Field(..., description="Reason for transfer")
    summary: str = Field(..., description="Summary of conversation for human agent")
    customer_email: Optional[str] = None
    order_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())