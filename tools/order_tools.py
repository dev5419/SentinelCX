import uuid
from typing import Dict, Any, Optional

from config import REFUND_AUTO_APPROVE_LIMIT
from policy.policy_gate import evaluate_refund_policy
from utils.mock_db import (
    get_order,
    get_user,
    record_refund,
    log_audit
)


def is_human_supervisor(approved_by: Optional[str]) -> bool:
    """Validates that approved_by represents an authorized human supervisor, not machine/system."""
    if not approved_by or not isinstance(approved_by, str):
        return False
    normalized = approved_by.strip().lower()
    disallowed = {"llm", "ai", "bot", "system", "auto", "automated", "none", "null", ""}
    if normalized in disallowed:
        return False
    return (
        normalized.startswith("sup_")
        or normalized.startswith("supervisor_")
        or normalized.startswith("human_")
        or "supervisor" in normalized
        or "human" in normalized
    )


def lookup_order(
    order_id: str,
    user_id: str,
    session: str = "default",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Deterministic tool: Looks up an order and verifies user ownership.
    Logs audit event.
    """
    order = get_order(order_id, db_path=db_path)
    input_data = {"order_id": order_id, "user_id": user_id}

    if not order:
        reason = f"Order {order_id} not found."
        log_audit(session, "lookup_order", input_data, "NOT_FOUND", reason, db_path=db_path)
        return {"found": False, "error": reason}

    if order["user_id"] != user_id:
        reason = f"Access denied: Order {order_id} belongs to user {order['user_id']}, not requesting user {user_id}."
        log_audit(session, "lookup_order", input_data, "ACCESS_DENIED", reason, db_path=db_path)
        return {"found": False, "error": reason}

    reason = f"Order {order_id} retrieved successfully for user {user_id}."
    log_audit(session, "lookup_order", input_data, "SUCCESS", reason, db_path=db_path)
    return {"found": True, "order": order}


def check_refund_policy(
    order_id: str,
    user_id: str,
    requested_amount: Optional[float] = None,
    session: str = "default",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Deterministic tool: Validates policy eligibility for an order refund.
    Returns {eligible, requires_human_approval, reason, policy_quote}.
    Logs audit event.
    """
    input_data = {"order_id": order_id, "user_id": user_id, "requested_amount": requested_amount}
    user = get_user(user_id, db_path=db_path)
    order = get_order(order_id, db_path=db_path)

    if not user:
        result = {
            "eligible": False,
            "requires_human_approval": False,
            "reason": f"User {user_id} not found.",
            "policy_quote": ""
        }
        log_audit(session, "check_refund_policy", input_data, "ERROR", result["reason"], db_path=db_path)
        return result

    if not order:
        result = {
            "eligible": False,
            "requires_human_approval": False,
            "reason": f"Order {order_id} not found.",
            "policy_quote": ""
        }
        log_audit(session, "check_refund_policy", input_data, "ERROR", result["reason"], db_path=db_path)
        return result

    # Evaluate pure policy gate
    gate_result = evaluate_refund_policy(
        order=order,
        user=user,
        requested_amount=requested_amount,
        session=session,
        db_path=db_path
    )

    decision = "APPROVED" if (gate_result["eligible"] and not gate_result["requires_human_approval"]) else (
        "REQUIRES_APPROVAL" if gate_result["eligible"] else "REJECTED"
    )
    log_audit(session, "check_refund_policy", input_data, decision, gate_result["reason"], db_path=db_path)
    return gate_result


def execute_refund(
    order_id: str,
    amount: float,
    reason: str,
    approved_by: Optional[str] = None,
    user_id: Optional[str] = None,
    session: str = "default",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Deterministic execution tool: Executes a refund only if:
    1. check_refund_policy passes (eligible is True).
    2. AND (amount <= REFUND_AUTO_APPROVE_LIMIT OR approved_by is a valid human supervisor id).
    
    Refuses execution if any check fails. Writes append-only audit_log entry.
    """
    input_data = {
        "order_id": order_id,
        "amount": amount,
        "reason": reason,
        "approved_by": approved_by,
        "user_id": user_id
    }

    order = get_order(order_id, db_path=db_path)
    if not order:
        msg = f"Refusal: Order {order_id} does not exist."
        log_audit(session, "execute_refund", input_data, "REFUSED", msg, db_path=db_path)
        return {"success": False, "status": "REFUSED", "reason": msg}

    # Resolve target user_id from order if not explicitly supplied
    target_user_id = user_id or order["user_id"]

    # 1. Gate check: Policy check must pass
    policy_res = check_refund_policy(
        order_id=order_id,
        user_id=target_user_id,
        requested_amount=amount,
        session=session,
        db_path=db_path
    )

    if not policy_res["eligible"]:
        refusal_msg = f"Refusal: Policy gate failed. {policy_res['reason']}"
        log_audit(session, "execute_refund", input_data, "REFUSED", refusal_msg, db_path=db_path)
        return {
            "success": False,
            "status": "REFUSED",
            "reason": refusal_msg,
            "policy_check": policy_res
        }

    # 2. Authorization check: amount <= limit OR human supervisor approval
    if amount > REFUND_AUTO_APPROVE_LIMIT:
        if not is_human_supervisor(approved_by):
            refusal_msg = (
                f"Refusal: Amount Rs {amount:.2f} exceeds auto-approval threshold of "
                f"Rs {REFUND_AUTO_APPROVE_LIMIT:.2f} and requires a verified human supervisor ID. "
                f"Provided approval: '{approved_by}' is not authorized."
            )
            log_audit(session, "execute_refund", input_data, "REFUSED", refusal_msg, db_path=db_path)
            return {
                "success": False,
                "status": "REFUSED",
                "reason": refusal_msg,
                "policy_check": policy_res
            }

    # All criteria satisfied: Record refund in mock DB
    refund_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
    final_approver = approved_by if approved_by else "system_auto"
    
    refund_record = record_refund(
        refund_id=refund_id,
        order_id=order_id,
        user_id=target_user_id,
        amount=amount,
        reason=reason,
        approved_by=final_approver,
        status="completed",
        db_path=db_path
    )

    exec_msg = f"Refund {refund_id} for Rs {amount:.2f} processed successfully. Approved by: {final_approver}."
    log_audit(session, "execute_refund", input_data, "EXECUTED", exec_msg, db_path=db_path)

    return {
        "success": True,
        "status": "EXECUTED",
        "refund_id": refund_id,
        "order_id": order_id,
        "user_id": target_user_id,
        "amount": amount,
        "reason": reason,
        "approved_by": final_approver,
        "details": refund_record
    }
