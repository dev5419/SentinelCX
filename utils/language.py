import re
from typing import Dict
from config import LLM


# Curated set of high-signal Hinglish tokens (Hindi vocabulary written in Latin script)
HINGLISH_VOCAB = {
    "mera", "meri", "mere", "mujhe", "karo", "karna", "kar", "nahi", "nahin", "nhi",
    "hai", "hain", "ho", "gaya", "gayi", "gaye", "hoga", "hogi", "bhai", "yaar",
    "kripya", "kaise", "kab", "kaha", "kyun", "kyu", "chahiye", "paise", "kat",
    "mila", "milega", "aaya", "aayi", "bhejo", "dedo", "batao", "dekh", "liye",
    "aur", "tha", "thi", "ek", "bohot", "bahut", "turant",
    "jaldi", "wapas", "kisko", "kisne", "khata", "paisa", "aapka", "humara", "kijiye"
}

# Rule-based fallback keywords translation for offline/mock environments
HINGLISH_TO_ENGLISH_KEYWORDS = {
    "refund": "refund",
    "wapas": "refund return",
    "paise": "money payment",
    "parcel": "package shipment",
    "order": "order",
    "mila": "received delivered",
    "nahi": "not",
    "deduct": "deducted charged",
    "kat": "deducted charged",
    "login": "login sign in",
    "password": "password reset",
    "bhool": "forgot reset",
    "subscription": "subscription plan",
    "cancel": "cancel cancelation",
    "billing": "billing payment invoice",
    "account": "account",
    "chahiye": "need want request"
}


def detect_language(query: str) -> str:
    """
    Detects language of user query:
    - 'hi' (Devanagari Hindi)
    - 'hinglish' (Hindi written in Roman script)
    - 'en' (English default)
    """
    if not query:
        return "en"

    # 1. Devanagari Unicode block
    if re.search(r"[\u0900-\u097F]", query):
        return "hi"

    # 2. Hinglish vocabulary heuristic
    words = re.findall(r"\b[a-zA-Z]+\b", query.lower())
    hinglish_matches = [w for w in words if w in HINGLISH_VOCAB]

    if len(hinglish_matches) >= 1:
        return "hinglish"

    return "en"


def normalize_to_english(query: str, language: str) -> str:
    """
    Normalizes a query into English for optimal semantic vector retrieval.
    If query is already English, returns query unmodified.
    Uses LLM translation with reliable heuristic fallback.
    """
    if language == "en":
        return query

    # Try LLM normalization
    try:
        prompt = (
            f"Translate the following customer query into clear, concise English for searching an FAQ documentation database.\n"
            f"Preserve order IDs like ORD-xxx. Do not answer, only output the English search query.\n\n"
            f"Customer query: {query}\n"
            f"English search query:"
        )
        response = LLM.invoke(prompt).content.strip()
        cleaned = response.strip('"').strip("'").strip()
        if cleaned and len(cleaned) > 2:
            return cleaned
    except Exception:
        pass

    # Heuristic fallback if LLM is unavailable or mocked
    words = query.lower().split()
    translated_tokens = []
    for w in words:
        clean_w = re.sub(r"[^\w-]", "", w)
        if clean_w.upper().startswith("ORD-"):
            translated_tokens.append(clean_w.upper())
        elif clean_w in HINGLISH_TO_ENGLISH_KEYWORDS:
            translated_tokens.append(HINGLISH_TO_ENGLISH_KEYWORDS[clean_w])
        elif len(clean_w) > 3 and clean_w.isalpha():
            translated_tokens.append(clean_w)

    fallback = " ".join(translated_tokens)
    return fallback if fallback else query
