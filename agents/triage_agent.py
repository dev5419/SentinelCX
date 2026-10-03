import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator

from config import LLM
from utils.mock_db import get_order


LEGAL_FRAUD_KEYWORDS = [
    "fraud", "scam", "cheat", "cheating", "lawyer", "legal", "court",
    "police", "fir", "chargeback", "consumer court", "consumer forum",
    "sue", "advocate", "stolen", "cyber cell", "dhokhadhadi"
]

ABUSIVE_KEYWORDS = [
    "idiot", "stupid", "useless", "scammers", "bastard", "chor",
    "kutte", "harami", "kamina", "bakwas", "incompetent"
]

SLA_DELTAS = {
    "Critical": timedelta(minutes=15),
    "High": timedelta(hours=1),
    "Medium": timedelta(hours=4),
    "Low": timedelta(hours=24)
}

ORDER_ID_REGEX = re.compile(r"\bORD[-_][A-Za-z0-9]+\b|\bORD\d+\b", re.IGNORECASE)


class TriageOutput(BaseModel):
    intent: Literal["faq", "refund_request", "billing_dispute", "login", "subscription", "unknown"] = "unknown"
    intent_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    sentiment: Literal["positive", "neutral", "frustrated", "abusive"] = "neutral"
    priority: Literal["Low", "Medium", "High", "Critical"] = "Medium"
    is_transactional: bool = False
    extracted_order_id: Optional[str] = None
    amount_at_risk: Optional[float] = None

    @field_validator("intent", mode="before")
    def normalize_intent(cls, v):
        if not v:
            return "unknown"
        clean = str(v).lower().strip()
        mapping = {
            "refund": "refund_request",
            "refunds": "refund_request",
            "refund_request": "refund_request",
            "billing": "billing_dispute",
            "billing_dispute": "billing_dispute",
            "login": "login",
            "subscription": "subscription",
            "faq": "faq",
            "unknown": "unknown"
        }
        return mapping.get(clean, "unknown")

    @field_validator("priority", mode="before")
    def normalize_priority(cls, v):
        if not v:
            return "Medium"
        clean = str(v).strip().capitalize()
        return clean if clean in ["Low", "Medium", "High", "Critical"] else "Medium"

    @field_validator("sentiment", mode="before")
    def normalize_sentiment(cls, v):
        if not v:
            return "neutral"
        clean = str(v).lower().strip()
        return clean if clean in ["positive", "neutral", "frustrated", "abusive"] else "neutral"

    @field_validator("extracted_order_id", mode="before")
    def normalize_order_id(cls, v):
        if not v:
            return None
        clean = str(v).strip().upper()
        if clean in ["NONE", "NULL", "N/A", "ORDER", ""]:
            return None
        # Ensure it starts with ORD
        if clean.startswith("ORD"):
            return clean
        return None


def _extract_amount_from_query(query: str) -> Optional[float]:
    """Extracts numeric currency amounts from query text, avoiding order ID digits."""
    # 1. With currency symbols: Rs 15000, ₹25000, $500, INR 12000
    curr_matches = re.findall(r"(?:rs\.?|inr|₹|\$)\s*(\d+(?:,\d+)*(?:\.\d+)?)", query, re.IGNORECASE)
    if curr_matches:
        try:
            return float(curr_matches[0].replace(",", ""))
        except ValueError:
            pass

    # 2. Strip order IDs so ORD-1001 digits don't get misparsed as currency
    cleaned = ORDER_ID_REGEX.sub("", query)

    # 3. Numeric amounts with context (e.g. 15000 ka order, 25000 amount, 15000 has not arrived)
    context_match = re.search(r"(?:amount|price|worth|paid|cost)?\s*(\d{4,7})\s*(?:amount|rupees|rs|bucks|paise|ka)?", cleaned, re.IGNORECASE)
    if context_match:
        try:
            val = float(context_match.group(1))
            if val >= 500:
                return val
        except ValueError:
            pass

    return None


def _call_llm_for_triage(
    query: str,
    history_context: Optional[str] = None,
    error_context: Optional[str] = None
) -> Optional[TriageOutput]:
    """Issues one structured-JSON LLM call to triage the customer query with defensive retry."""
    prompt = f"""You are an enterprise customer support triage classifier.
Analyze the user query (which may be in English or Hinglish).
Return a JSON object with EXACTLY these fields:
- "intent": one of ["faq", "refund_request", "billing_dispute", "login", "subscription", "unknown"]
  * "faq": General questions about policies, delivery timelines, store info, how to check invoices.
  * "refund_request": Customer asking for a refund, return, or parcel not arrived/received for an order.
  * "billing_dispute": Double charges, wrong deductions, unauthorized transactions, invoice disputes, chargebacks.
  * "login": Password reset, OTP issues, account lockout, cannot sign in.
  * "subscription": Cancelling, renewing, or managing recurring subscriptions.
  * "unknown": Vague statements without actionable customer support context.
- "intent_confidence": float between 0.0 and 1.0
- "sentiment": one of ["positive", "neutral", "frustrated", "abusive"]
  * "abusive": Insults, offensive slurs (e.g. idiot, scammers, chor, kutte).
  * "frustrated": Angry, disappointed, double charged, missing delivery.
  * "positive": Grateful, thanking support.
  * "neutral": Standard calm inquiry.
- "priority": one of ["Low", "Medium", "High", "Critical"]
  * "Critical": Extreme urgency or large amount-at-risk (>10000).
  * "High": Billing disputes, legal/chargeback threats, abusive messages.
  * "Medium": Standard refund requests, account login assistance, subscription changes.
  * "Low": General FAQs, polite inquiries, feedback.
- "is_transactional": boolean (true for refunds, billing disputes, subscription cancellations, order actions; false for FAQs, login help, general inquiries)
- "extracted_order_id": string (e.g. "ORD-1001", "ORD-501" or null if no order ID in query)
- "amount_at_risk": number (e.g. 15000 or null if no amount stated)

{history_context if history_context else ""}
{"ERROR IN PREVIOUS ATTEMPT: " + error_context if error_context else ""}

User Query:
{query}

Respond ONLY with a valid JSON object (no markdown, no preamble).
"""
    for attempt in range(2):
        try:
            resp = LLM.invoke(prompt).content.strip()
            match = re.search(r"\{.*\}", resp, re.DOTALL)
            if match:
                json_str = match.group(0)
                data = json.loads(json_str)
                return TriageOutput(**data)
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                time.sleep(1.0)
                continue
            return None
    return None


def _heuristic_triage_fallback(query: str, history: Optional[list] = None) -> TriageOutput:
    """Robust deterministic fallback if LLM or JSON parsing fails."""
    q_lower = query.lower()

    # Extract Order ID
    order_match = ORDER_ID_REGEX.search(query)
    extracted_order_id = order_match.group(0).upper() if order_match else None

    # Sentiment
    if any(k in q_lower for k in ABUSIVE_KEYWORDS):
        sentiment = "abusive"
    elif any(k in q_lower for k in [
        "not happy", "frustrated", "angry", "terrible", "worst", "disappointed",
        "parce nahi mila", "pareshaan", "nahi mila", "not arrived", "stole",
        "twice", "do baar", "double payment", "charged twice", "lawyer", "police",
        "fir", "chargeback", "fraud", "deliver nahi hua", "nahi aaya", "amount at risk",
        "unauthorized", "stolen"
    ]):
        sentiment = "frustrated"
    elif any(k in q_lower for k in ["thank you", "thanks", "great", "helpful", "good"]):
        sentiment = "positive"
    else:
        sentiment = "neutral"

    # Intent
    if any(k in q_lower for k in ["policy", "return policy", "delivery time", "how does", "what is", "what are", "what happens", "how long"]):
        intent = "faq"
        is_transactional = False
        priority = "Low"
    elif any(k in q_lower for k in ["login", "password", "sign in", "otp", "reset password", "account", "credentials", "2fa", "authentication", "stuck loading", "access revoked"]):
        intent = "login"
        is_transactional = False
        priority = "Medium"
    elif any(k in q_lower for k in ["refund", "wapas", "paise wapas", "return", "not arrived", "deliver nahi hua", "parcel deliver", "nahi aaya"]):
        intent = "refund_request"
        is_transactional = True
        priority = "Medium"
    elif any(k in q_lower for k in ["billing", "charged twice", "double payment", "do baar", "extra charge", "deducted twice", "chargeback", "stole my money", "fraud", "scam", "invoice", "payment", "fee", "charged", "bill", "gst", "bank transfer"]):
        intent = "billing_dispute"
        is_transactional = True
        priority = "High"
    elif any(k in q_lower for k in ["subscription", "renew", "membership", "cancel sub", "cancel my monthly", "downgrade", "plan"]):
        intent = "subscription"
        is_transactional = True
        priority = "Medium"
    elif any(k in q_lower for k in ["how to", "kitne din"]):
        intent = "faq"
        is_transactional = False
        priority = "Low"
    elif history and extracted_order_id:
        hist_text = " ".join(str(h.get("content", "")) for h in history).lower()
        if "refund" in hist_text or "order id" in hist_text or "order" in hist_text:
            intent = "refund_request"
            is_transactional = True
            priority = "Medium"
        else:
            intent = "unknown"
            is_transactional = False
            priority = "Low"
    else:
        intent = "unknown"
        is_transactional = False
        priority = "Low"

    return TriageOutput(
        intent=intent,
        intent_confidence=0.85 if intent != "unknown" else 0.4,
        sentiment=sentiment,
        priority=priority,
        is_transactional=is_transactional,
        extracted_order_id=extracted_order_id,
        amount_at_risk=_extract_amount_from_query(query)
    )


def triage_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Triage Agent: Single structured-JSON call classifying intent, sentiment,
    priority, transactionality, and extracted order ID.
    
    Applies deterministic Python overrides:
    - Abusive sentiment or legal/fraud/chargeback keywords -> priority >= High
    - Amount at risk > 10,000 -> priority = Critical
    - Computes SLA deadline per priority
    """
    query = state.get("sanitized_query") or state.get("user_query", "")
    history = state.get("history", [])
    recent_turns = history[-4:] if history else []
    history_context = ""
    if recent_turns:
        history_context = "\nRecent Conversation Turns:\n" + "\n".join(
            f"{t.get('role', 'user').capitalize()}: {t.get('content', '')}" for t in recent_turns
        )

    # 1. Call LLM (with 1 retry on parse failure)
    triage_obj = _call_llm_for_triage(query, history_context=history_context)
    if not triage_obj:
        triage_obj = _call_llm_for_triage(
            query,
            history_context=history_context,
            error_context="JSON parsing failed. Return valid JSON only."
        )

    # If still None, use deterministic heuristic fallback
    if not triage_obj:
        triage_obj = _heuristic_triage_fallback(query, history=history)

    # 2. Extract or confirm Order ID from query using precise regex
    order_id = triage_obj.extracted_order_id
    if not order_id or order_id == "ORDER":
        order_match = ORDER_ID_REGEX.search(query)
        order_id = order_match.group(0).upper() if order_match else None
        triage_obj.extracted_order_id = order_id

    # 3. Determine Amount at Risk (from query or mock_db order record)
    amount_at_risk = triage_obj.amount_at_risk or _extract_amount_from_query(query)
    if order_id and amount_at_risk is None:
        try:
            ord_row = get_order(order_id)
            if ord_row:
                amount_at_risk = float(ord_row.get("amount", 0.0))
        except Exception:
            pass

    # 4. DETERMINISTIC OVERRIDES IN PYTHON
    priority = triage_obj.priority
    q_lower = query.lower()

    # Override Rule 1: Abusive sentiment OR legal/fraud/chargeback keywords -> priority >= High
    has_legal_keyword = any(kw in q_lower for kw in LEGAL_FRAUD_KEYWORDS)
    is_abusive = (triage_obj.sentiment == "abusive") or any(kw in q_lower for kw in ABUSIVE_KEYWORDS)

    if is_abusive:
        triage_obj.sentiment = "abusive"

    if (is_abusive or has_legal_keyword) and priority in ["Low", "Medium"]:
        priority = "High"

    # Override Rule 2: Amount at risk > 10,000 -> Critical
    if amount_at_risk is not None and amount_at_risk > 10000.0:
        priority = "Critical"

    # 5. Compute SLA deadline based on final priority
    now = datetime.now(timezone.utc)
    sla_delta = SLA_DELTAS.get(priority, timedelta(hours=4))
    sla_deadline = (now + sla_delta).isoformat()

    # 6. Ensure transactional consistency:
    # Informational questions (FAQ) are NOT transactional even if they mention refund or billing words!
    is_faq = (triage_obj.intent == "faq") or any(
        k in q_lower
        for k in [
            "how long", "what is", "what are", "policy", "how do", "how to", "how does",
            "what happens", "can i", "can we", "is it possible", "eligibility",
            "kitne din", "kab tak", "timeline", "window for"
        ]
    )
    if is_faq and not order_id and not any(k in q_lower for k in ["chahiye", "kardo", "please refund", "my refund", "refund now", "charged twice"]):
        triage_obj.intent = "faq"
        is_transactional = False
    elif triage_obj.intent in ["refund_request", "billing_dispute"] or order_id is not None:
        is_transactional = True
    else:
        is_transactional = triage_obj.is_transactional

    return {
        "intent": triage_obj.intent,
        "intent_confidence": triage_obj.intent_confidence,
        "sentiment": triage_obj.sentiment,
        "priority": priority,
        "is_transactional": is_transactional,
        "extracted_order_id": order_id,
        "amount_at_risk": amount_at_risk,
        "sla_deadline": sla_deadline
    }
