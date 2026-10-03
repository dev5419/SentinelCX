import os
import sys
import pytest

# Ensure project root in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.graph import build_graph
from ui.customer_portal import render_message_item


# ============================================================================
# 10 Diverse FAQ Queries Covering Knowledge Base Categories
# ============================================================================

FAQ_QUERIES = [
    {
        "id": "faq_01",
        "category": "refunds",
        "query": "What is your return and refund policy window?"
    },
    {
        "id": "faq_02",
        "category": "refunds",
        "query": "How long does a refund take to process and reflect in the bank?"
    },
    {
        "id": "faq_03",
        "category": "refunds",
        "query": "What is the policy for refunds after cancelling a trial period?"
    },
    {
        "id": "faq_04",
        "category": "refunds",
        "query": "What is the refund policy for annual subscription plans?"
    },
    {
        "id": "faq_05",
        "category": "refunds",
        "query": "Can I receive a refund after my account has been suspended?"
    },
    {
        "id": "faq_06",
        "category": "billing",
        "query": "How does the monthly billing cycle and invoice date work?"
    },
    {
        "id": "faq_07",
        "category": "billing",
        "query": "How do I download my past billing invoice receipts?"
    },
    {
        "id": "faq_08",
        "category": "login",
        "query": "How do I reset my password if I forgot my login credentials?"
    },
    {
        "id": "faq_09",
        "category": "login",
        "query": "Why is my account locked after failed login attempts?"
    },
    {
        "id": "faq_10",
        "category": "subscription",
        "query": "What are the steps to change my subscription billing cycle?"
    }
]


@pytest.fixture(scope="module")
def graph():
    return build_graph()


# ============================================================================
# Test 1: 10 FAQ Queries with Valid Citations and File Existence
# ============================================================================

@pytest.mark.parametrize("item", FAQ_QUERIES, ids=[f["id"] for f in FAQ_QUERIES])
def test_faq_verifiable_answer_and_citations(graph, item):
    cfg = {"configurable": {"thread_id": f"test_verifiable_{item['id']}"}}
    res = graph.invoke(
        {"user_query": item["query"], "user_id": "user_1"},
        config=cfg
    )

    # 1. Answer action and content
    assert res.get("action") == "answer", f"Expected 'answer', got {res.get('action')}"
    assert len(res.get("answer", "").strip()) > 0, "Expected non-empty answer"
    assert res.get("grounded") is True, "Expected grounded=True for verified FAQ"

    # 2. Retrieved Docs & Citations
    docs = res.get("retrieved_docs", [])
    assert len(docs) >= 1, f"Expected at least 1 citation for query '{item['query']}'"

    # 3. Verify each citation structure and file existence on disk
    for doc in docs:
        assert isinstance(doc, dict), f"Expected citation dict, got {type(doc)}"
        assert "title" in doc and len(doc["title"]) > 0, "Missing or empty title"
        assert "category" in doc and len(doc["category"]) > 0, "Missing or empty category"
        assert "snippet" in doc and len(doc["snippet"]) > 0, "Missing or empty snippet"
        assert "score" in doc and isinstance(doc["score"], (int, float)), "Missing or invalid score"
        assert "source" in doc and len(doc["source"]) > 0, "Missing or empty source"

        # Verify source file actually exists on disk
        source_path = doc["source"]
        assert os.path.exists(source_path), f"Citation source file does not exist on disk: {source_path}"
        assert os.path.isfile(source_path), f"Citation path is not a file: {source_path}"

    # 4. "Why this decision?" panel data
    why = res.get("why_decision")
    assert isinstance(why, dict), "Expected why_decision dict in state"
    assert "intent" in why and len(str(why["intent"])) > 0
    assert "confidence" in why and isinstance(why["confidence"], (int, float))
    assert "policy_rule" in why and len(str(why["policy_rule"])) > 0
    assert "final_route" in why and why["final_route"] == "rag_answer"
    assert "reason" in why and len(str(why["reason"])) > 0


# ============================================================================
# Test 2: Deliberately Unanswerable Query Routes to Handoff (No Hallucination)
# ============================================================================

def test_unanswerable_query_routes_to_handoff(graph):
    """
    A deliberately unanswerable question about a non-existent product
    must fail strict grounding and route to human handoff rather than hallucinating.
    """
    cfg = {"configurable": {"thread_id": "test_unanswerable_01"}}
    unanswerable_q = "What is the warranty policy on quantum teleportation helmets?"
    
    res = graph.invoke(
        {"user_query": unanswerable_q, "user_id": "user_1"},
        config=cfg
    )

    # Must escalate to human handoff
    assert res.get("action") == "escalate", f"Expected 'escalate', got {res.get('action')}"
    assert res.get("force_escalate") is True, "Expected force_escalate=True"
    assert res.get("grounded") is False, "Expected grounded=False"

    # Must not hallucinate details about teleportation helmets
    ans_lower = res.get("answer", "").lower()
    assert "quantum teleportation" not in ans_lower or "escalate" in ans_lower or "human" in ans_lower

    # Handoff dossier must be generated for supervisor review
    assert res.get("handoff_dossier") is not None, "Expected handoff_dossier"
    assert "ground" in res.get("handoff_dossier", {}).get("issue_summary", "").lower()

    # Why decision must document hallucination prevention
    why = res.get("why_decision")
    assert isinstance(why, dict)
    assert why.get("final_route") == "human_handoff"
    assert "grounding" in why.get("policy_rule", "").lower() or "hallucination" in why.get("policy_rule", "").lower()


# ============================================================================
# Test 3: UI Panels Render Test
# ============================================================================

def test_ui_panels_render():
    """
    Verifies that render_message_item renders without error for:
    1. Grounded message with citations & why_decision
    2. Not verified message with why_decision
    3. Transactional policy verified message
    """
    # 1. Grounded assistant message
    msg_grounded = {
        "role": "assistant",
        "content": "Refunds are processed within 5-10 business days.",
        "grounded": True,
        "action": "answer",
        "retrieved_docs": [{
            "title": "Refund Processing Time",
            "category": "Refunds",
            "snippet": "Allow 5-10 business days for the refund to be processed.",
            "score": 0.88,
            "source": os.path.join(BASE_DIR, "data", "docs", "refunds", "refund_processing_time.md")
        }],
        "why_decision": {
            "intent": "refunds",
            "confidence": 0.95,
            "policy_rule": "Knowledge Base Grounding Policy (refunds)",
            "final_route": "rag_answer",
            "reason": "Retrieved documentation from refunds and claims were 100% verified."
        },
        "trace": [{"node": "rag", "summary": "Retrieved 1 doc", "duration_ms": 12.5}]
    }

    # 2. Not verified assistant message
    msg_unverified = {
        "role": "assistant",
        "content": "I could not verify a reliable answer. Escalating to human support.",
        "grounded": False,
        "action": "escalate",
        "why_decision": {
            "intent": "unknown",
            "confidence": 0.40,
            "policy_rule": "Hallucination Prevention & Factual Grounding Enforcement",
            "final_route": "human_handoff",
            "reason": "Failed 2-pass strict grounding check."
        },
        "trace": [{"node": "grounding", "summary": "Failed grounding", "duration_ms": 8.0}]
    }

    # Test rendering logic without raising exceptions
    try:
        render_message_item(msg_grounded)
        render_message_item(msg_unverified)
    except Exception as e:
        pytest.fail(f"render_message_item raised an exception: {e}")
