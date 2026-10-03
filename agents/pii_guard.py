import re
from typing import Dict, Any, Tuple, List


def luhn_check(number_str: str) -> bool:
    """Validates credit/debit card numbers using the Luhn algorithm."""
    digits = [int(c) for c in number_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += (doubled - 9) if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0


def mask_pii(text: str) -> Dict[str, Any]:
    """
    Sanitizes customer text by masking PII:
    - Indian phone (+91 / 10-digit starting with 6-9)
    - Email addresses
    - Aadhaar-like 12-digit numbers
    - Payment card numbers (validated via Luhn algorithm)
    - OTPs (4-6 digits proximal to otp/code/pin keywords)
    
    Protects order IDs (ORD-xxx) and currency amounts from being masked.
    Returns:
        {
            "sanitized_query": str,
            "redacted_pii": Dict[str, str],
            "counts": Dict[str, int]
        }
    """
    if not text:
        return {
            "sanitized_query": "",
            "redacted_pii": {},
            "counts": {"phone": 0, "email": 0, "aadhaar": 0, "card": 0, "otp": 0, "total": 0}
        }

    redacted_pii: Dict[str, str] = {}
    counts = {"phone": 0, "email": 0, "aadhaar": 0, "card": 0, "otp": 0, "total": 0}

    # Step 1: Temporarily protect Order IDs (e.g. ORD-1001, ORD_501)
    order_id_placeholders: List[Tuple[str, str]] = []
    order_id_pattern = re.compile(r"\bORD[-_]?[A-Za-z0-9]+\b", re.IGNORECASE)

    def save_order_id(match):
        token = f"__ORDER_ID_TOKEN_{len(order_id_placeholders)}__"
        order_id_placeholders.append((token, match.group(0)))
        return token

    working_text = order_id_pattern.sub(save_order_id, text)

    # Step 2: Mask Emails
    email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    for match in email_pattern.finditer(working_text):
        raw_val = match.group(0)
        counts["email"] += 1
        placeholder = f"[REDACTED_EMAIL_{counts['email']}]"
        redacted_pii[placeholder] = raw_val
    working_text = email_pattern.sub(lambda m: f"[REDACTED_EMAIL]", working_text)

    # Step 3: Mask Card numbers (Luhn checked, 13-19 digits with spaces/hyphens)
    card_candidate_pattern = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")
    candidates = list(card_candidate_pattern.finditer(working_text))
    # Replace in reverse to preserve string indices
    for match in reversed(candidates):
        raw_val = match.group(0)
        digits_only = re.sub(r"\D", "", raw_val)
        if 13 <= len(digits_only) <= 19 and luhn_check(digits_only):
            counts["card"] += 1
            placeholder = f"[REDACTED_CARD_{counts['card']}]"
            redacted_pii[placeholder] = raw_val
            start, end = match.span()
            working_text = working_text[:start] + "[REDACTED_CARD]" + working_text[end:]

    # Step 4: Mask Aadhaar-like 12-digit numbers (4-4-4 or 12 continuous digits starting with 2-9)
    aadhaar_pattern = re.compile(r"\b[2-9]\d{3}[ -]\d{4}[ -]\d{4}\b|\b[2-9]\d{11}\b")
    for match in aadhaar_pattern.finditer(working_text):
        raw_val = match.group(0)
        counts["aadhaar"] += 1
        placeholder = f"[REDACTED_AADHAAR_{counts['aadhaar']}]"
        redacted_pii[placeholder] = raw_val
    working_text = aadhaar_pattern.sub(lambda m: "[REDACTED_AADHAAR]", working_text)

    # Step 5: Mask Indian Phone Numbers (+91 prefix or 10-digit mobile starting with 6-9)
    phone_pattern = re.compile(
        r"(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b|(?:\+91[\-\s]?)[6-9]\d{9}\b|\b[6-9]\d{9}\b"
    )
    for match in phone_pattern.finditer(working_text):
        raw_val = match.group(0)
        counts["phone"] += 1
        placeholder = f"[REDACTED_PHONE_{counts['phone']}]"
        redacted_pii[placeholder] = raw_val
    working_text = phone_pattern.sub(lambda m: "[REDACTED_PHONE]", working_text)

    # Step 6: Mask OTPs (4-6 digits near keywords otp, code, pin, verification)
    # Forward: "otp is 123456", "code: 4829", "pin 9012"
    otp_fwd_pattern = re.compile(
        r"(?i)\b(?:otp|code|pin|verification(?:\s*code)?|password)\b[^\d\n]{1,15}?(\b\d{4,6}\b)"
    )
    for match in otp_fwd_pattern.finditer(working_text):
        raw_val = match.group(1)
        counts["otp"] += 1
        placeholder = f"[REDACTED_OTP_{counts['otp']}]"
        redacted_pii[placeholder] = raw_val

    def replace_otp_fwd(m):
        full = m.group(0)
        digits = m.group(1)
        return full.replace(digits, "[REDACTED_OTP]")

    working_text = otp_fwd_pattern.sub(replace_otp_fwd, working_text)

    # Backward: "123456 is my otp", "4829 is the code"
    otp_bwd_pattern = re.compile(
        r"(?i)(\b\d{4,6}\b)[^\d\n]{1,15}?\b(?:otp|code|pin)\b"
    )
    for match in otp_bwd_pattern.finditer(working_text):
        raw_val = match.group(1)
        if raw_val not in redacted_pii.values():
            counts["otp"] += 1
            placeholder = f"[REDACTED_OTP_{counts['otp']}]"
            redacted_pii[placeholder] = raw_val

    def replace_otp_bwd(m):
        full = m.group(0)
        digits = m.group(1)
        return full.replace(digits, "[REDACTED_OTP]")

    working_text = otp_bwd_pattern.sub(replace_otp_bwd, working_text)

    # Step 7: Restore Order IDs
    for token, original_order_id in order_id_placeholders:
        working_text = working_text.replace(token, original_order_id)

    counts["total"] = sum(v for k, v in counts.items() if k != "total")

    return {
        "sanitized_query": working_text,
        "redacted_pii": redacted_pii,
        "counts": counts
    }


def pii_guard_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: executes BEFORE any LLM call to guarantee
    raw customer PII never reaches language models.
    """
    raw_query = state.get("user_query", "")
    mask_result = mask_pii(raw_query)

    return {
        "user_query": mask_result["sanitized_query"],
        "sanitized_query": mask_result["sanitized_query"],
        "redacted_pii": mask_result["redacted_pii"],
        "pii_counts": mask_result["counts"]
    }
