from datetime import datetime, timezone
import math
from typing import Dict, Any, Optional

from config import REFUND_WINDOW_DAYS, REFUND_AUTO_APPROVE_LIMIT
from utils.mock_db import log_audit


def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def evaluate_refund_policy(
    order: Dict[str, Any],
    user: Dict[str, Any],
    requested_amount: Optional[float] = None,
    session: str = "default",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Pure Python deterministic policy gate enforcing refund constraints.
    Returns:
        {
            "eligible": bool,
            "requires_human_approval": bool,
            "reason": str,
            "policy_quote": str
        }
    Also writes an immutable audit record for the gate decision.
    """
    order_id = order.get("order_id", "UNKNOWN")
    user_id = user.get("user_id", "UNKNOWN")
    try:
        amount = float(requested_amount) if requested_amount is not None else float(order.get("amount", 0.0))
        valid_amount = math.isfinite(amount) and 0 < amount <= float(order.get("amount", 0.0))
    except (ValueError, TypeError, OverflowError):
        amount, valid_amount = None, False
    if not valid_amount:
        result = {"eligible": False, "requires_human_approval": False,
                  "reason": "Refund amount must be finite, positive, and no greater than the order total.",
                  "policy_quote": "Refunds cannot exceed the original purchase amount."}
        log_audit(session, "policy_gate.evaluate_refund_policy", {"order_id": order_id, "user_id": user_id},
                  "REJECTED", result["reason"], db_path=db_path)
        return result

    # Rule 1: User ownership match
    if order.get("user_id") != user.get("user_id"):
        result = {
            "eligible": False,
            "requires_human_approval": False,
            "reason": f"Ownership mismatch: Order {order_id} belongs to user {order.get('user_id')}, not requesting user {user_id}.",
            "policy_quote": "Refund requests may only be initiated by the account holder who placed the order."
        }
        decision = "REJECTED"
        log_audit(session, "policy_gate.evaluate_refund_policy", 
                  {"order_id": order_id, "user_id": user_id, "amount": amount},
                  decision, result["reason"], db_path=db_path)
        return result

    # Rule 2: User must be verified
    if not bool(user.get("is_verified")):
        result = {
            "eligible": False,
            "requires_human_approval": False,
            "reason": f"User {user_id} account is unverified. Only verified accounts are eligible for refunds.",
            "policy_quote": "Only verified customer accounts in good standing are eligible to request refunds."
        }
        decision = "REJECTED"
        log_audit(session, "policy_gate.evaluate_refund_policy",
                  {"order_id": order_id, "user_id": user_id, "amount": amount},
                  decision, result["reason"], db_path=db_path)
        return result

    # Rule 3: Order status must be 'delivered' and not already refunded or cancelled
    order_status = str(order.get("status", "")).lower()
    if order_status == "refunded":
        result = {
            "eligible": False,
            "requires_human_approval": False,
            "reason": f"Order {order_id} has already been refunded.",
            "policy_quote": "Items that have already been refunded are not eligible for duplicate refund requests."
        }
        decision = "REJECTED"
        log_audit(session, "policy_gate.evaluate_refund_policy",
                  {"order_id": order_id, "user_id": user_id, "amount": amount},
                  decision, result["reason"], db_path=db_path)
        return result

    if order_status == "cancelled":
        result = {
            "eligible": False,
            "requires_human_approval": False,
            "reason": f"Order {order_id} was cancelled prior to delivery and is not returnable.",
            "policy_quote": "Cancelled orders are not eligible for return or refund as no items were delivered."
        }
        decision = "REJECTED"
        log_audit(session, "policy_gate.evaluate_refund_policy",
                  {"order_id": order_id, "user_id": user_id, "amount": amount},
                  decision, result["reason"], db_path=db_path)
        return result

    if order_status != "delivered":
        result = {
            "eligible": False,
            "requires_human_approval": False,
            "reason": f"Order {order_id} status is '{order_status}', not delivered.",
            "policy_quote": "Refunds and returns can only be processed after an order has been successfully delivered."
        }
        decision = "REJECTED"
        log_audit(session, "policy_gate.evaluate_refund_policy",
                  {"order_id": order_id, "user_id": user_id, "amount": amount},
                  decision, result["reason"], db_path=db_path)
        return result

    # Rule 4: Delivery date within 14-day window
    delivery_date_str = order.get("delivery_date")
    delivery_dt = _parse_datetime(delivery_date_str)
    now = datetime.now(timezone.utc)

    if not delivery_dt:
        result = {
            "eligible": False,
            "requires_human_approval": False,
            "reason": f"Order {order_id} has no valid delivery date recorded.",
            "policy_quote": "Refund eligibility is calculated based on the confirmed delivery date."
        }
        decision = "REJECTED"
        log_audit(session, "policy_gate.evaluate_refund_policy",
                  {"order_id": order_id, "user_id": user_id, "amount": amount},
                  decision, result["reason"], db_path=db_path)
        return result

    days_since_delivery = (now - delivery_dt).days
    if days_since_delivery > REFUND_WINDOW_DAYS:
        result = {
            "eligible": False,
            "requires_human_approval": False,
            "reason": f"Return window expired ({days_since_delivery} days since delivery, limit is {REFUND_WINDOW_DAYS} days).",
            "policy_quote": f"Refund requests must be submitted within {REFUND_WINDOW_DAYS} days of delivery."
        }
        decision = "REJECTED"
        log_audit(session, "policy_gate.evaluate_refund_policy",
                  {"order_id": order_id, "user_id": user_id, "amount": amount},
                  decision, result["reason"], db_path=db_path)
        return result

    # Rule 5: Amount check (<= 2000 auto else HITL)
    if amount <= REFUND_AUTO_APPROVE_LIMIT:
        result = {
            "eligible": True,
            "requires_human_approval": False,
            "reason": f"Order is eligible for automatic refund (Amount Rs {amount:.2f} <= Rs {REFUND_AUTO_APPROVE_LIMIT:.2f}).",
            "policy_quote": f"Refunds up to Rs {REFUND_AUTO_APPROVE_LIMIT:.2f} for delivered items within {REFUND_WINDOW_DAYS} days are automatically approved."
        }
        decision = "APPROVED"
    else:
        result = {
            "eligible": True,
            "requires_human_approval": True,
            "reason": f"Order is eligible, but amount Rs {amount:.2f} exceeds auto-approval threshold of Rs {REFUND_AUTO_APPROVE_LIMIT:.2f}; human supervisor approval required.",
            "policy_quote": f"Refund requests exceeding Rs {REFUND_AUTO_APPROVE_LIMIT:.2f} require supervisor review and approval."
        }
        decision = "REQUIRES_APPROVAL"

    log_audit(session, "policy_gate.evaluate_refund_policy",
              {"order_id": order_id, "user_id": user_id, "amount": amount},
              decision, result["reason"], db_path=db_path)
    return result
