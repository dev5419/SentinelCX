from config import LLM

def is_grounded(answer: str, context: str) -> bool:
    if not answer or not context:
        return False

    prompt = f"""
    You are checking for hallucinations.

    Context:
    {context}

    Answer:
    {answer}

    Question:
    Is every factual claim in the answer supported by the context?

    Reply in ONLY one word :
    YES or NO
    """

    try:
        verdict = LLM.invoke(prompt).content.strip().upper()
        return "YES" in verdict
    except Exception:
        # Graceful fallback on rate limit or network error
        ans_words = set(w.lower() for w in answer.split() if len(w) > 3)
        ctx_words = set(w.lower() for w in context.split() if len(w) > 3)
        common = ans_words.intersection(ctx_words)
        return len(common) >= 2