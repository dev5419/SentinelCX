from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


def generate_handoff_dossier(
    state: Dict[str, Any],
    issue_summary: Optional[str] = None,
    proposed_action: Optional[str] = None,
    proposed_amount: Optional[float] = None,
    policy_decision: Optional[Dict[str, Any]] = None,
    tool_history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generates a structured, PII-safe handoff dossier for human supervisors or escalated tickets.
    Reused across:
    1. HITL supervisor approval (high-value refunds)
    2. Abusive customer messages
    3. Ungrounded / hallucinated RAG answers
    4. General escalations / security guard blocks
    """
    user_id = state.get("user_id", "user_1")
    sanitized_query = state.get("sanitized_query") or state.get("user_query", "")
    pii_counts = state.get("pii_counts", {})
    redacted_pii = state.get("redacted_pii", {})

    sentiment = state.get("sentiment", "neutral")
    priority = state.get("priority", "Medium")
    sla_deadline = state.get("sla_deadline")
    if not sla_deadline:
        now = datetime.now(timezone.utc)
        sla_deadline = now.isoformat()

    # Default issue summary if not provided
    if not issue_summary:
        issue_summary = f"Customer inquiry requiring human review: '{sanitized_query[:100]}'"

    # Retrieved evidence (docs, citations)
    retrieved_evidence = state.get("retrieved_docs", [])

    # Tool history
    tools = tool_history if tool_history is not None else state.get("tool_history", [])

    # Amount
    amount = proposed_amount if proposed_amount is not None else state.get("amount_at_risk")

    # Policy decision
    decision = policy_decision if policy_decision is not None else state.get("policy_decision")

    # Proposed action
    if not proposed_action:
        order_id = state.get("extracted_order_id")
        if order_id and amount:
            proposed_action = f"Review and authorize refund of Rs {amount:.2f} for order {order_id}"
        else:
            proposed_action = "Investigate issue and contact customer via support ticket"

    return {
        "issue_summary": issue_summary,
        "sentiment": sentiment,
        "priority": priority,
        "sla_deadline": sla_deadline,
        "customer_details": {
            "user_id": user_id,
            "sanitized_query": sanitized_query,
            "pii_counts": pii_counts,
            "masked_fields": list(redacted_pii.keys()) if redacted_pii else []
        },
        "retrieved_evidence": retrieved_evidence,
        "tool_history": tools,
        "proposed_action": proposed_action,
        "amount": amount,
        "policy_decision": decision
    }
