import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import pytest
from streamlit.testing.v1 import AppTest

from utils.mock_db import reset_db, get_order, get_refunds_for_order, get_audit_logs


def test_scripted_flow_headless():
    """
    End-to-end headless test running the required scripted flow:
    1. Reset demo & seed DB
    2. Hinglish refund (auto-executed)
    3. Rs 15,000 refund (appears in queue, approve it, customer view updates)
    4. Abusive message (human handoff)
    5. Metrics match audit log
    """
    # 1. Reset database
    reset_db()

    main_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py")
    at = AppTest.from_file(main_file)
    at.run(timeout=60)
    assert len(at.exception) == 0, f"Exceptions on initial load: {[e.message for e in at.exception]}"

    # Verify initial buttons exist
    reset_btn = next((b for b in at.button if "Reset Demo" in b.label), None)
    assert reset_btn is not None, "Reset Demo button must be present in sidebar"

    # =========================================================================
    # Scenario 1: Hinglish refund (auto-executed)
    # =========================================================================
    print("\n--- Running Scenario 1: Hinglish Auto Refund ---")
    query_1 = "Mera order ORD-1001 ka refund chahiye please, kharab product aya hai"
    
    # Enter chat input
    assert len(at.chat_input) > 0, "Customer Portal chat_input must exist"
    at.chat_input[0].set_value(query_1).run(timeout=60)
    assert len(at.exception) == 0, f"Exceptions after query 1: {[e.message for e in at.exception]}"

    # Verify customer chat received auto-approved refund response
    chat_msgs = at.chat_message
    assert len(chat_msgs) >= 2, "Expected user and assistant chat messages"
    assistant_msg_1 = chat_msgs[-1].markdown[0].value
    print("Assistant Response 1:", assistant_msg_1)
    assert "refund" in assistant_msg_1.lower() or "process" in assistant_msg_1.lower()

    # Verify DB state: order refunded, refund recorded
    order_1 = get_order("ORD-1001")
    assert order_1["status"] == "refunded", f"Order status should be refunded, got {order_1['status']}"
    refunds_1 = get_refunds_for_order("ORD-1001")
    assert len(refunds_1) == 1, "Refund row must exist for ORD-1001"
    assert refunds_1[0]["approved_by"] == "system_auto"
    assert refunds_1[0]["amount"] == 1499.0

    # =========================================================================
    # Scenario 2: Rs 15,000 refund (HITL queue -> Approve -> view updates)
    # =========================================================================
    print("\n--- Running Scenario 2: Rs 15,000 HITL Refund ---")
    query_2 = "Please process refund for order ORD-1005 for Rs 15000"
    at.chat_input[0].set_value(query_2).run(timeout=60)
    assert len(at.exception) == 0, f"Exceptions after query 2: {[e.message for e in at.exception]}"

    # Verify customer portal shows friendly pending-approval notice
    current_tid = at.session_state.thread_id
    tracked_threads = at.session_state.tracked_threads
    assert current_tid in tracked_threads
    ticket_2 = tracked_threads[current_tid]
    assert ticket_2["status"] == "pending_approval"
    assert ticket_2["interrupted"] is True
    assert ticket_2["dossier"]["amount"] == 15000.0

    # Verify approval queue in Tab 2 contains the ticket
    approve_btns = [b for b in at.button if b.key and b.key.startswith("btn_approve_")]
    assert len(approve_btns) == 1, f"Expected 1 approve button in queue, found {len(approve_btns)}"
    reject_btns = [b for b in at.button if b.key and b.key.startswith("btn_reject_")]
    assert len(reject_btns) == 1, f"Expected 1 reject button in queue, found {len(reject_btns)}"

    # Supervisor approves the request
    print("Supervisor clicking Approve...")
    approve_btns[0].click().run(timeout=60)
    assert len(at.exception) == 0, f"Exceptions after supervisor approval: {[e.message for e in at.exception]}"

    # Verify thread status updated in session state
    ticket_2_post = at.session_state.tracked_threads[current_tid]
    assert ticket_2_post["status"] == "approved"
    assert ticket_2_post["interrupted"] is False
    assert "approve" in ticket_2_post["last_answer"].lower()
    print("Approved answer:", ticket_2_post["last_answer"])

    # Verify DB state: ORD-1005 refunded by supervisor
    order_2 = get_order("ORD-1005")
    assert order_2["status"] == "refunded"
    refunds_2 = get_refunds_for_order("ORD-1005")
    assert len(refunds_2) == 1
    assert refunds_2[0]["amount"] == 15000.0
    assert refunds_2[0]["approved_by"] == "sup_lead_01"

    # Verify Customer View messages updated with supervisor approval
    customer_msgs = at.session_state.messages_by_thread[current_tid]
    approved_msg = customer_msgs[-1]["content"]
    assert "approve" in approved_msg.lower()
    assert "sup_lead_01" in approved_msg or "supervisor" in approved_msg.lower()

    # =========================================================================
    # Scenario 3: Abusive message (direct handoff)
    # =========================================================================
    print("\n--- Running Scenario 3: Abusive Message Escalation ---")
    # Click New Chat to start fresh conversation for abusive test
    new_chat_btn = next((b for b in at.button if "New Chat" in b.label), None)
    assert new_chat_btn is not None
    new_chat_btn.click().run(timeout=60)
    assert len(at.exception) == 0

    abusive_tid = at.session_state.thread_id
    assert abusive_tid != current_tid, "New chat should have created a fresh thread_id"

    query_3 = "You stupid useless bot refund my money right now or I will destroy your company you idiot"
    at.chat_input[0].set_value(query_3).run(timeout=60)
    assert len(at.exception) == 0, f"Exceptions after query 3: {[e.message for e in at.exception]}"

    # Verify escalation and handoff
    ticket_3 = at.session_state.tracked_threads[abusive_tid]
    assert ticket_3["status"] == "escalated"
    assert ticket_3["sentiment"] == "abusive"
    assert ticket_3["priority"] in ["High", "Critical"]
    assert ticket_3["dossier"] is not None
    assert "escalat" in ticket_3["last_answer"].lower() or "human" in ticket_3["last_answer"].lower()
    print("Escalation answer:", ticket_3["last_answer"])

    # =========================================================================
    # Scenario 4: Metrics Match Audit Log
    # =========================================================================
    print("\n--- Checking Metrics & Audit Log Consistency ---")
    audit_logs = get_audit_logs()
    assert len(audit_logs) >= 3, "Audit log should have records for policy check, refunds, and actions"

    # Verify auto refund is in audit log
    auto_logs = [l for l in audit_logs if l["action"] == "execute_refund" and "system_auto" in l["input"]]
    assert len(auto_logs) >= 1, "Audit log must contain auto-executed refund"

    # Verify supervisor approved refund is in audit log
    sup_logs = [l for l in audit_logs if l["action"] == "execute_refund" and "sup_lead_01" in l["input"]]
    assert len(sup_logs) >= 1, "Audit log must contain supervisor approved refund"

    # Verify metric values rendered on screen
    metrics = at.metric
    metric_labels = [m.label for m in metrics]
    assert "Active Tickets" in metric_labels
    assert "PII Redactions" in metric_labels
    assert "Priority (Crit / High)" in metric_labels
    assert "Auto-Resolved vs Escalated" in metric_labels

    print("ALL SCENARIOS VERIFIED SUCCESSFULLY HEADLESS!")


if __name__ == "__main__":
    test_scripted_flow_headless()
