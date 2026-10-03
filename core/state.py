import operator
from typing import TypedDict, Literal, List, Dict, Any, Optional, Annotated


class SupportState(TypedDict, total=False):
    # User Inputs & Session Context
    user_query: str
    user_id: str
    session_id: str

    # Sanitization & Security
    sanitized_query: str
    redacted_pii: Dict[str, str]
    pii_counts: Dict[str, int]
    language: str
    query_en: str

    # Triage Agent Fields
    intent: Literal["faq", "refund_request", "billing_dispute", "login", "subscription", "unknown"]
    intent_confidence: float
    sentiment: Literal["positive", "neutral", "frustrated", "abusive"]
    priority: Literal["Low", "Medium", "High", "Critical"]
    is_transactional: bool
    extracted_order_id: Optional[str]
    amount_at_risk: Optional[float]
    sla_deadline: str

    # Policy & HITL
    policy_decision: Optional[Dict[str, Any]]
    handoff_dossier: Optional[Dict[str, Any]]
    tool_history: Annotated[List[Dict[str, Any]], operator.add]

    # RAG & Grounding
    retrieved_docs: List[Dict[str, Any]]
    grounded: Optional[bool]
    context: Optional[str]

    # Explainability & Decision Trace
    why_decision: Optional[Dict[str, Any]]

    # Output & Flow Control
    answer: str
    answer_confidence: float
    force_escalate: bool
    action: Literal["answer", "clarify", "escalate", "reject"]

    # Multi-turn History (MemorySaver checkpointer)
    history: Annotated[List[Dict[str, Any]], operator.add]
    messages: Annotated[List[Dict[str, Any]], operator.add]

    # UI Timeline Trace
    trace: Annotated[List[Dict[str, Any]], operator.add]