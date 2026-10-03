from config import LLM

def clarification_agent(state):
    prompt = f"""
    Ask a polite clarifying question to better understand the user's issue:
    {state["user_query"]}
    """

    try:
        ans = LLM.invoke(prompt).content
    except Exception:
        ans = "Could you please provide more details about your request so we can assist you better?"

    return {
        "answer": ans,
        "action": "clarify"
    }
