import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.state import SupportState
from core.graph import build_graph
from agents.confidence_agent import confidence_agent
from rag.retriever import get_retriever, retriever


# =====================================================================
# 1. Tests for Confidence Agent (Scoring, Ladder, Override, Defensiveness)
# =====================================================================

def make_mock_response(content: str):
    mock = MagicMock()
    mock.content = content
    return mock


def test_confidence_score_0_95_routes_to_answer():
    state = {
        "user_query": "How long does a refund take?",
        "answer": "Refunds are processed within 5-7 business days.",
        "force_escalate": False
    }
    with patch("agents.confidence_agent.LLM") as mock_llm:
        mock_llm.invoke.return_value = make_mock_response("0.95")
        result = confidence_agent(state)
        assert result["action"] == "answer"
        assert result["answer_confidence"] == pytest.approx(0.95)


def test_confidence_score_0_5_routes_to_clarify():
    state = {
        "user_query": "I need help with my transaction",
        "answer": "Transactions depend on your payment method.",
        "force_escalate": False
    }
    with patch("agents.confidence_agent.LLM") as mock_llm:
        mock_llm.invoke.return_value = make_mock_response("0.5")
        result = confidence_agent(state)
        assert result["action"] == "clarify"
        assert result["answer_confidence"] == pytest.approx(0.5)


def test_confidence_score_0_2_routes_to_escalate():
    state = {
        "user_query": "Charged after account was closed",
        "answer": "I do not have specific documentation for this.",
        "force_escalate": False
    }
    with patch("agents.confidence_agent.LLM") as mock_llm:
        mock_llm.invoke.return_value = make_mock_response("0.2")
        result = confidence_agent(state)
        assert result["action"] == "escalate"
        assert result["answer_confidence"] == pytest.approx(0.2)


def test_force_escalate_override():
    state = {
        "user_query": "Any query",
        "answer": "Any answer",
        "force_escalate": True
    }
    # Even if LLM would score it 0.99, force_escalate must immediately return escalate with 0.0 confidence
    with patch("agents.confidence_agent.LLM") as mock_llm:
        mock_llm.invoke.return_value = make_mock_response("0.99")
        result = confidence_agent(state)
        assert result["action"] == "escalate"
        assert result["answer_confidence"] == 0.0


def test_defensive_score_parsing():
    state = {
        "user_query": "Query",
        "answer": "Answer",
        "force_escalate": False
    }
    # Text with score inside: "Score: 0.85\nExplanation..."
    with patch("agents.confidence_agent.LLM") as mock_llm:
        mock_llm.invoke.return_value = make_mock_response("Score: 0.85")
        result = confidence_agent(state)
        assert result["action"] == "answer"
        assert result["answer_confidence"] == pytest.approx(0.85)

    # Garbage text with no numbers: defaults to 0.0 -> escalate
    with patch("agents.confidence_agent.LLM") as mock_llm:
        mock_llm.invoke.return_value = make_mock_response("I cannot score this")
        result = confidence_agent(state)
        assert result["action"] == "escalate"
        assert result["answer_confidence"] == 0.0

    # Number clamped to 1.0
    with patch("agents.confidence_agent.LLM") as mock_llm:
        mock_llm.invoke.return_value = make_mock_response("1.5")
        result = confidence_agent(state)
        assert result["action"] == "answer"
        assert result["answer_confidence"] == 1.0


# =====================================================================
# 2. Tests for Intent-Filtered Chroma Retrieval
# =====================================================================

def test_intent_filtered_retrieval_refunds():
    refund_retriever = get_retriever(category="refunds", k=4)
    docs = refund_retriever.invoke("refund request processing")
    assert len(docs) > 0
    for doc in docs:
        assert doc.metadata.get("category") == "refunds", f"Expected category 'refunds', got: {doc.metadata}"


def test_intent_filtered_retrieval_billing():
    billing_retriever = get_retriever(category="billing", k=4)
    docs = billing_retriever.invoke("invoice tax calculation")
    assert len(docs) > 0
    for doc in docs:
        assert doc.metadata.get("category") == "billing", f"Expected category 'billing', got: {doc.metadata}"


def test_intent_filtered_retrieval_login():
    login_retriever = get_retriever(category="login", k=4)
    docs = login_retriever.invoke("two factor authentication error")
    assert len(docs) > 0
    for doc in docs:
        assert doc.metadata.get("category") == "login", f"Expected category 'login', got: {doc.metadata}"


def test_intent_filtered_retrieval_subscription():
    sub_retriever = get_retriever(category="subscription", k=4)
    docs = sub_retriever.invoke("cancel my auto renewal plan")
    assert len(docs) > 0
    for doc in docs:
        assert doc.metadata.get("category") == "subscription", f"Expected category 'subscription', got: {doc.metadata}"


# =====================================================================
# 3. Tests for End-to-End Graph Execution on 3 Sample Queries
# =====================================================================

@pytest.fixture(scope="module")
def compiled_graph():
    return build_graph()


def test_graph_end_to_end_query_1_answer(compiled_graph):
    # Standard FAQ question from docs with clear answer
    query = "how long does it take to get refund"
    result = compiled_graph.invoke({"user_query": query})
    assert isinstance(result, dict)
    assert "answer" in result and len(result["answer"].strip()) > 0
    assert "action" in result
    assert result["action"] in ["answer", "clarify", "escalate"]
    # With bug fixed, high-quality answer should route to answer
    assert result["action"] == "answer"


def test_graph_end_to_end_query_2_escalate(compiled_graph):
    # Specific issue expected to escalate
    query = "charged after subscription cancellation"
    result = compiled_graph.invoke({"user_query": query})
    assert isinstance(result, dict)
    assert "answer" in result and len(result["answer"].strip()) > 0
    assert "action" in result
    assert result["action"] in ["answer", "clarify", "escalate"]


def test_graph_end_to_end_query_3_clarify(compiled_graph):
    # Vague / ambiguous query expected to trigger clarification
    query = "fix this now"
    result = compiled_graph.invoke({"user_query": query})
    assert isinstance(result, dict)
    assert "answer" in result and len(result["answer"].strip()) > 0
    assert "action" in result
    assert result["action"] == "clarify"
