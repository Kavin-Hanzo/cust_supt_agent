from typing import Optional, Dict, Any
from src.utils.models import HandoffPayload


def escalate_to_human(
    reason: str,
    summary: str,
    customer_email: Optional[str] = None,
    order_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transfers conversation to a human support agent.
    """
    return HandoffPayload(
        triggered=True,
        reason=reason,
        summary=summary,
        customer_email=customer_email,
        order_id=order_id
    ).model_dump()