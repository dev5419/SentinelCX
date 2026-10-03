import re
from config import LLM

def confidence_agent(state):

    if state.get("force_escalate"):
        return {
            "answer_confidence": 0.0,
            "action": "escalate"
        }

    prompt = f"""
    Score the answer quality from 0 to 1.

    Question:
    {state["user_query"]}

    Answer:
    {state["answer"]}

    Return ONLY a number.
    """

    try:
        raw_resp = LLM.invoke(prompt).content.strip()
        match = re.search(r"[-+]?(?:\d*\.\d+|\d+)", raw_resp)
        if match:
            score = max(0.0, min(1.0, float(match.group())))
        else:
            score = 0.85 if len(state.get("answer", "")) > 15 else 0.0
    except Exception:
        score = 0.85 if len(state.get("answer", "")) > 15 else 0.0

    ## Tone Control
    if score < 0.65:
        state["answer"] = (
            "Based on our documentation, here's what I can share:\n\n"
            + state["answer"]
            + "\n\nIf this doesn't resolve your issue, I can escalate it."
        )

    if score >= 0.65:
        action = "answer"
    elif score >= 0.4:
        action = "clarify"
    else:
        action = "escalate"

    return {
        "answer": state["answer"],
        "answer_confidence": score,
        "action": action
    }


