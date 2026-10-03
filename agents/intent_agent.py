import json
import re
from config import LLM
from agents.pii_guard import mask_pii
from utils.language import detect_language


def intent_agent(state):
    # Ensure query is sanitized before LLM invocation
    raw_query = state.get("sanitized_query") or state.get("user_query", "")
    masked_result = mask_pii(raw_query)
    query = masked_result["sanitized_query"]

    # Detect language if not already in state
    language = state.get("language") or detect_language(query)

    prompt = f"""
    Classify customer support query intent as one of:
    billing, login, subscription, refunds, unknown

    The user query may be in English, Hindi, or Hinglish (Hindi written in Roman script).
    Examples of Hinglish queries:
    - "Bhai mera order ORD-501 ka amount deduct ho gaya par parcel nahi mila, refund chahiye" -> refunds
    - "Mera account login nahi ho raha hai password bhool gaya please help karo" -> login
    - "Subscription cancel kaise kare? Agle mahine ka payment nahi katna chahiye" -> subscription
    - "Mera double billing ho gaya hai ek hi order ke liye do baar paise kat gaye" -> billing

    Return JSON:
    {{"intent": "<category>", "confidence": <float between 0 and 1>}}

    Query:
    {query}
    """

    try:
        resp = LLM.invoke(prompt).content.strip()
    except Exception:
        resp = ""

    intent = "unknown"
    confidence = 0.0

    # 1. Attempt JSON extraction
    match = re.search(r"\{.*?\}", resp, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            raw_intent = str(data.get("intent", "")).lower().strip()
            raw_conf = float(data.get("confidence", 0.0))
            if raw_intent in ["billing", "login", "subscription", "refunds", "unknown"]:
                intent = raw_intent
                confidence = max(0.0, min(1.0, raw_conf))
        except Exception:
            pass

    # 2. Fallback heuristic from LLM text and query keywords (including Hinglish)
    if intent == "unknown":
        resp_lower = resp.lower()
        q_lower = query.lower()

        # Check Subscription first to avoid 'payment' keyword stealing subscription cancel queries
        if (any(k in resp_lower for k in ["subscription", "renew", "membership", "sub"]) or
            any(k in q_lower for k in ["subscription", "membership", "renew", "cancel sub"])):
            intent = "subscription"
            confidence = 0.85
        # Refunds
        elif (any(k in resp_lower for k in ["refund", "wapas"]) or
              any(k in q_lower for k in ["refund", "wapas", "paise wapas", "parcel nahi mila", "return"])):
            intent = "refunds"
            confidence = 0.85
        # Billing
        elif (any(k in resp_lower for k in ["billing", "charge", "invoice"]) or
              any(k in q_lower for k in ["billing", "bill", "invoice", "charge", "kata", "kat gaya", "deduct", "payment", "do baar"])):
            intent = "billing"
            confidence = 0.85
        # Login
        elif (any(k in resp_lower for k in ["login", "sign in", "password"]) or
              any(k in q_lower for k in ["login", "password", "otp", "sign in", "khata", "bhool gaya"])):
            intent = "login"
            confidence = 0.85

    return {
        "intent": intent,
        "intent_confidence": confidence,
        "sanitized_query": query,
        "language": language
    }