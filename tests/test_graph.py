import os
import sys
import pytest

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from langgraph.types import Command
from core.graph import build_graph
from utils.mock_db import (
    reset_db,
    get_order,
    get_refunds_for_order,
    get_audit_logs
)


@pytest.fixture
def graph():
    """Returns a freshly compiled graph."""
    return build_graph()


# ============================================================================
# Scenario (a): FAQ answered with citations
# ============================================================================

def test_scenario_a_faq_answered_with_citations(graph):
    """
    Scenario (a): FAQ query retrieves documents from ChromaDB,
    verifies grounding, and formats response with citations.
    """
    cfg = {"configurable": {"thread_id": "faq_thread_01"}}
    query = "What is your return policy?"
    res = graph.invoke({"user_query": query, "user_id": "user_1"}, config=cfg)

    assert res["action"] == "answer"
    assert len(res["answer"].strip()) > 0
    assert len(res["retrieved_docs"]) > 0, "Expected citation sources in retrieved_docs"
    
    # Verify trace timeline logging
    trace_nodes = [t["node"] for t in res["trace"]]
    assert "pii" in trace_nodes
    assert "injection" in trace_nodes
    assert "triage" in trace_nodes
    assert "rag" in trace_nodes
    assert "grounding" in trace_nodes
    assert "respond" in trace_nodes

    for entry in res["trace"]:
        assert "duration_ms" in entry
        assert entry["duration_ms"] >= 0.0


# ============================================================================
# Scenario (b): Rs 1,499 eligible refund auto-executed
# ============================================================================

def test_scenario_b_eligible_refund_auto_executed(graph):
    """
    Scenario (b): Delivered 3 days ago, amount Rs 1,499 (<= Rs 2,000 threshold).
    Deterministic policy passes -> auto_execute node runs execute_refund.
    DB shows completed refund and refunded order status. Audit log records EXECUTED.
    """
    reset_db()
    cfg = {"configurable": {"thread_id": "auto_refund_thread_01"}}
    query = "Please process a refund for my order ORD-1001"
    
    res = graph.invoke({"user_query": query, "user_id": "user_1"}, config=cfg)

    assert res["action"] == "answer"
    assert "1499" in res["answer"] or "refund" in res["answer"].lower()

    # 1. Verify DB state: refunds table
    refunds = get_refunds_for_order("ORD-1001")
    assert len(refunds) == 1
    assert refunds[0]["amount"] == 1499.0
    assert refunds[0]["approved_by"] == "system_auto"
    assert refunds[0]["status"] == "completed"

    # 2. Verify DB state: orders table status updated
    order = get_order("ORD-1001")
    assert order["status"] == "refunded"

    # 3. Verify append-only audit_log
    audit = get_audit_logs(limit=25)
    exec_audits = [a for a in audit if a["action"] == "execute_refund"]
    assert len(exec_audits) >= 1
    assert any(a["decision"] == "EXECUTED" for a in exec_audits)


# ============================================================================
# Scenario (c): Expired order rejected with policy quote
# ============================================================================

def test_scenario_c_expired_order_rejected_with_policy_quote(graph):
    """
    Scenario (c): Delivered 30 days ago (> 14 days refund window).
    Policy gate rejects with exact policy quote. DB has no new refund.
    Audit log records REJECTED.
    """
    reset_db()
    cfg = {"configurable": {"thread_id": "expired_refund_thread_01"}}
    query = "I need a refund for order ORD-1002"

    res = graph.invoke({"user_query": query, "user_id": "user_1"}, config=cfg)

    assert res["action"] in ["reject", "answer"]
    assert "14 days" in res["answer"], "Response must quote 14-day policy limit"

    # 1. Verify DB state: NO refund created
    refunds = get_refunds_for_order("ORD-1002")
    assert len(refunds) == 0

    # 2. Verify order status unchanged
    order = get_order("ORD-1002")
    assert order["status"] == "delivered"

    # 3. Verify audit log records REJECTED decision
    audit = get_audit_logs(limit=25)
    rejections = [a for a in audit if a["decision"] == "REJECTED"]
    assert len(rejections) >= 1
    assert any("expired" in a["reason"].lower() or "14" in a["reason"] for a in rejections)


# ============================================================================
# Scenario (d): Rs 15,000 refund pauses at interrupt, then approve/reject
# ============================================================================

def test_scenario_d1_high_value_refund_hitl_approve(graph):
    """
    Scenario (d1): High-value order ORD-1005 (Rs 15,000 > Rs 2,000 limit).
    Pauses at interrupt with handoff_dossier.
    Resuming with Command(resume={"status": "approved", "supervisor": id}) executes refund.
    """
    reset_db()
    cfg = {"configurable": {"thread_id": "hitl_approve_thread_01"}}
    query = "Please process refund for order ORD-1005 for Rs 15000"

    # 1. Initial invocation pauses at interrupt
    res = graph.invoke({"user_query": query, "user_id": "user_1"}, config=cfg)

    # Verify graph state is paused at interrupt
    state = graph.get_state(cfg)
    assert len(state.tasks) > 0
    assert len(state.tasks[0].interrupts) > 0

    interrupt_payload = state.tasks[0].interrupts[0].value
    assert "dossier" in interrupt_payload
    dossier = interrupt_payload["dossier"]
    assert dossier["amount"] == 15000.0
    assert dossier["customer_details"]["user_id"] == "user_1"
    assert dossier["priority"] in ["High", "Critical"]
    assert "sla_deadline" in dossier
    assert dossier["policy_decision"]["requires_human_approval"] is True

    # 2. Resume with supervisor approval
    res_resumed = graph.invoke(
        Command(resume={"status": "approved", "supervisor": "sup_lead_88"}),
        config=cfg
    )

    assert res_resumed["action"] == "answer"
    assert "sup_lead_88" in res_resumed["answer"]
    assert "refund" in res_resumed["answer"].lower()

    # 3. Verify DB state: refund created with supervisor ID
    refunds = get_refunds_for_order("ORD-1005")
    assert len(refunds) == 1
    assert refunds[0]["amount"] == 15000.0
    assert refunds[0]["approved_by"] == "sup_lead_88"
    assert refunds[0]["status"] == "completed"

    # 4. Verify DB state: order status updated
    order = get_order("ORD-1005")
    assert order["status"] == "refunded"

    # 5. Verify audit log
    audit = get_audit_logs(limit=25)
    exec_audits = [a for a in audit if a["action"] == "execute_refund" and a["decision"] == "EXECUTED"]
    assert len(exec_audits) >= 1
    assert any("sup_lead_88" in a["reason"] for a in exec_audits)


def test_scenario_d2_high_value_refund_hitl_reject(graph):
    """
    Scenario (d2): High-value order ORD-1005 pauses at interrupt.
    Resuming with Command(resume={"status": "rejected", "supervisor": id}) declines refund.
    DB has no refund record. Audit log logs REJECTED_BY_SUPERVISOR.
    """
    reset_db()
    cfg = {"configurable": {"thread_id": "hitl_reject_thread_01"}}
    query = "Please process refund for order ORD-1005 for Rs 15000"

    # 1. Initial invoke pauses at interrupt
    res = graph.invoke({"user_query": query, "user_id": "user_1"}, config=cfg)
    state = graph.get_state(cfg)
    assert len(state.tasks[0].interrupts) > 0

    # 2. Resume with supervisor rejection
    res_rejected = graph.invoke(
        Command(resume={"status": "rejected", "supervisor": "sup_manager_12"}),
        config=cfg
    )

    assert res_rejected["action"] in ["reject", "answer"]
    assert "declined" in res_rejected["answer"].lower() or "rejected" in res_rejected["answer"].lower()

    # 3. Verify DB state: NO refund record created
    refunds = get_refunds_for_order("ORD-1005")
    assert len(refunds) == 0

    # 4. Verify order status remains delivered
    order = get_order("ORD-1005")
    assert order["status"] == "delivered"

    # 5. Verify audit log records supervisor rejection
    audit = get_audit_logs(limit=25)
    sup_rejects = [a for a in audit if a["decision"] == "REJECTED_BY_SUPERVISOR"]
    assert len(sup_rejects) >= 1
    assert "sup_manager_12" in sup_rejects[0]["reason"]


# ============================================================================
# Scenario (e): Clarify turn then user reply resumes with context
# ============================================================================

def test_scenario_e_clarify_turn_resumes_with_context(graph):
    """
    Scenario (e): Multi-turn conversation on the same thread_id.
    Turn 1: "I want a refund" (missing order ID) -> routes to clarify.
    Turn 2: "My order is ORD-1001" -> resumes with previous context and executes refund.
    """
    reset_db()
    cfg = {"configurable": {"thread_id": "multi_turn_clarify_thread_01"}}

    # Turn 1: Vague query missing order ID
    res1 = graph.invoke({"user_query": "I want a refund", "user_id": "user_1"}, config=cfg)
    assert res1["action"] == "clarify"
    assert "order id" in res1["answer"].lower() or "provide" in res1["answer"].lower()

    # Turn 2: User provides order ID on the SAME thread
    res2 = graph.invoke({"user_query": "My order is ORD-1001", "user_id": "user_1"}, config=cfg)
    assert res2["action"] == "answer"
    assert "refund" in res2["answer"].lower() or "1499" in res2["answer"]

    # Verify conversation history has accumulated all 4 messages
    assert len(res2["history"]) >= 4
    roles = [m["role"] for m in res2["history"]]
    assert roles[:4] == ["user", "assistant", "user", "assistant"]

    # Verify refund was executed for ORD-1001
    refunds = get_refunds_for_order("ORD-1001")
    assert len(refunds) == 1
    assert refunds[0]["amount"] == 1499.0
    assert refunds[0]["status"] == "completed"


# ============================================================================
# Scenario (f): Abusive message goes to handoff with dossier
# ============================================================================

def test_scenario_f_abusive_message_handoff_with_dossier(graph):
    """
    Scenario (f): Abusive query routes directly to escalate with handoff dossier.
    Dossier contains sentiment, priority, SLA, customer details, proposed action.
    """
    cfg = {"configurable": {"thread_id": "abusive_handoff_thread_01"}}
    query = "You idiot scammers, your useless service stole my money and you are completely incompetent!"

    res = graph.invoke({"user_query": query, "user_id": "user_1"}, config=cfg)

    assert res["action"] == "escalate"
    assert "handoff_dossier" in res and res["handoff_dossier"] is not None

    dossier = res["handoff_dossier"]
    assert dossier["sentiment"] == "abusive"
    assert dossier["priority"] in ["High", "Critical"]
    assert "sla_deadline" in dossier
    assert "customer_details" in dossier
    assert dossier["customer_details"]["user_id"] == "user_1"
    assert "proposed_action" in dossier
    assert "policy_decision" in dossier


# ============================================================================
# Scenario (g): UI Trace Timeline Verification
# ============================================================================

def test_ui_timeline_trace_format(graph):
    """
    Scenario (g): Validates that all traversed nodes write trace entries
    with (node, summary, duration_ms) to SupportState.trace.
    """
    cfg = {"configurable": {"thread_id": "trace_test_thread"}}
    res = graph.invoke({"user_query": "What is the return policy?", "user_id": "user_1"}, config=cfg)

    assert "trace" in res and len(res["trace"]) > 0
    for entry in res["trace"]:
        assert "node" in entry and isinstance(entry["node"], str)
        assert "summary" in entry and isinstance(entry["summary"], str)
        assert "duration_ms" in entry and isinstance(entry["duration_ms"], (int, float))
        assert entry["duration_ms"] >= 0.0
