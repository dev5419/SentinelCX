from config import LLM
from rag.retriever import get_retriever, retriever, build_citation
from agents.grounding_guard import is_grounded
from agents.pii_guard import mask_pii
from utils.language import detect_language, normalize_to_english


MIN_CONTEXT_LENGTH = 300  # characters

def rewrite_query(query: str) -> str:
    prompt = f"""
    Rewrite the following customer support query into clearer, concise English search keywords.
    Query:
    {query}
    """
    return LLM.invoke(prompt).content.strip()


def rag_agent(state):
    # Ensure query is sanitized before any operation
    raw_query = state.get("sanitized_query") or state.get("user_query", "")
    masked_result = mask_pii(raw_query)
    query = masked_result["sanitized_query"]

    # Detect language and English-normalized query for retrieval
    language = state.get("language") or detect_language(query)
    query_en = state.get("query_en") or normalize_to_english(query, language)

    intent = state.get("intent", "unknown")
    intent_confidence = state.get("intent_confidence", 0.0)

    # If intent == "unknown" and confidence is low, route to clarify
    if intent == "unknown" and intent_confidence < 0.6:
        clarify_msg = (
            "Kripya apni query thoda aur detail me batayein taaki hum aapki behtar madad kar sakein."
            if language == "hinglish" else
            "Could you please clarify your request so I can assist you better?"
        )
        return {
            "retrieved_docs": [],
            "answer": clarify_msg,
            "force_escalate": False,
            "action": "clarify"
        }

    # Filter Chroma retrieval by intent category metadata when intent_confidence >= 0.6, else search all
    category_map = {
        "refund_request": "refunds",
        "refunds": "refunds",
        "billing_dispute": "billing",
        "billing": "billing",
        "login": "login",
        "subscription": "subscription"
    }
    retrieval_cat = category_map.get(intent)
    if retrieval_cat and intent_confidence >= 0.6:
        active_retriever = get_retriever(category=retrieval_cat)
    else:
        active_retriever = retriever

    # Retrieval uses the English-normalized version of the query
    docs = active_retriever.invoke(query_en)
    context = "\n\n".join(d.page_content for d in docs)

    if len(context) < MIN_CONTEXT_LENGTH:
        rewritten = rewrite_query(query_en)
        docs = active_retriever.invoke(rewritten)
        context = "\n\n".join(d.page_content for d in docs)

    if len(context) < MIN_CONTEXT_LENGTH:
        fallback_msg = (
            "Humare knowledge base me is vishay par reliable jankari uplabdh nahi hai. Hum aapko human support agent se connect kar rahe hain."
            if language == "hinglish" else
            "I'm unable to find a reliable answer from our knowledge base."
        )
        return {
            "retrieved_docs": [],
            "answer": fallback_msg,
            "force_escalate": True,
            "language": language
        }

    prompt = f"""
    Answer ONLY using the context below.
    Do NOT add any information not explicitly stated.

    Context:
    {context}

    Question:
    {query}

    Language Instruction:
    User language style: {language.upper()}
    - If user query is in Hinglish (Roman Hindi), reply politely in natural conversational Hinglish matching their style.
    - If user query is in Hindi (Devanagari script), reply in Hindi.
    - If user query is in English, reply in English.
    Maintain a warm, polite customer support tone.
    """
    try:
        answer = LLM.invoke(prompt).content
    except Exception:
        answer = context.split("\n\n")[0].strip() if context else "Based on our documentation, here is what we found."

    # Guardrail: Groundedness
    grounded = is_grounded(answer, context)

    if not grounded:
        ungrounded_msg = (
            "Dokumentation ke anusaar hum iska nishchit uttar nahi de sakte. Hum request ko escalate kar rahe hain."
            if language == "hinglish" else
            "I'm not confident this can be answered reliably from our documentation."
        )
        return {
            "retrieved_docs": [],
            "answer": ungrounded_msg,
            "force_escalate": True,
            "language": language
        }

    return {
        "retrieved_docs": [build_citation(d) for d in docs],
        "answer": answer,
        "force_escalate": False,
        "language": language,
        "query_en": query_en,
        "sanitized_query": query
    }
