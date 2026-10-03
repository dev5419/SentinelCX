def escalation_agent(state):
    return {
        "answer": (
            "Your issue requires human assistance. "
            "A support ticket has been created."
        ),
        "action": "escalate"
    }