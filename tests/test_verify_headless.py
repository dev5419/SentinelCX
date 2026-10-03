import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Pre-load embeddings and graph once so subsequent runs don't incur model-loading delays
from ui.shared import get_graph
g_init = get_graph()

from streamlit.testing.v1 import AppTest
from utils.mock_db import reset_db, get_order, get_refunds_for_order, get_audit_logs


def run_full_headless_verification():
    print("=================================================================")
    print("STARTING HEADLESS VERIFICATION OF ENTERPRISE CUSTOMER SUPPORT APP")
    print("=================================================================")

    # 1. Reset database
    print("\n[Step 1] Resetting SQLite Database and Seeding fresh demo data...")
    reset_db()
    print("Database reset and initial seed confirmed.")

    # 2. Launch Streamlit AppTest Headless
    print("\n[Step 2] Initializing Streamlit AppTest headless...")
    main_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py")
    at = AppTest.from_file(main_file)
    at.run(timeout=60)
    assert len(at.exception) == 0, f"Exceptions on startup: {[e.message for e in at.exception]}"
    print("App loaded successfully without exceptions!")

    # Verify Sidebar Reset Button
    reset_btn = next((b for b in at.button if "Reset Demo" in b.label), None)
    assert reset_btn is not None, "Reset Demo button missing!"
    print("Verified Reset Demo button is present in sidebar.")

    # Verify initial badges & metrics
    metric_labels = [m.label for m in at.metric]
    print("Initial Metrics present:", metric_labels)
    assert "Active Tickets" in metric_labels
    assert "PII Redactions" in metric_labels
    assert "Priority (Crit / High)" in metric_labels
    assert "Auto-Resolved vs Escalated" in metric_labels

    # =========================================================================
    # SCENARIO A: Hinglish Refund (Auto-Executed)
    # =========================================================================
    print("\n-----------------------------------------------------------------")
    print("[Scenario A] Testing Hinglish Refund (Auto-Executed)")
    print("Query: 'Mera order ORD-1001 ka refund chahiye please, kharab product aya hai'")
    print("-----------------------------------------------------------------")
    
    query_a = "Mera order ORD-1001 ka refund chahiye please, kharab product aya hai"
    at.chat_input[0].set_value(query_a).run(timeout=60)
    assert len(at.exception) == 0, f"Exceptions on Scenario A: {[e.message for e in at.exception]}"

    # Verify Customer Message History
    tid_a = at.session_state.thread_id
    msgs_a = at.session_state.messages_by_thread[tid_a]
    assert len(msgs_a) >= 2, f"Expected user and assistant message, got {len(msgs_a)}"
    
    assistant_reply_a = msgs_a[-1]["content"]
    print("Customer Portal Response:\n", assistant_reply_a)
    assert "refund" in assistant_reply_a.lower() or "process" in assistant_reply_a.lower()

    # Verify Trace Timeline
    trace_a = msgs_a[-1].get("trace", [])
    node_names_a = [t["node"] for t in trace_a]
    print("Agent steps trace timeline:", node_names_a)
    assert "triage" in node_names_a
    assert "policy_gate" in node_names_a
    assert "auto_execute" in node_names_a

    # Verify DB state
    order_a = get_order("ORD-1001")
    assert order_a["status"] == "refunded", f"Expected status 'refunded', got {order_a['status']}"
    refunds_a = get_refunds_for_order("ORD-1001")
    assert len(refunds_a) == 1, "Expected exactly 1 refund record"
    assert refunds_a[0]["approved_by"] == "system_auto"
    assert refunds_a[0]["amount"] == 1499.0
    print(f"PASS: Order ORD-1001 auto-refunded (Amount: Rs {refunds_a[0]['amount']}, Approved by: {refunds_a[0]['approved_by']})")

    # =========================================================================
    # SCENARIO B: Rs 15,000 Refund (HITL Queue -> Approve -> Customer View Updates)
    # =========================================================================
    print("\n-----------------------------------------------------------------")
    print("[Scenario B] Testing Rs 15,000 High-Value Refund (HITL Queue -> Approve)")
    print("Query: 'Please process refund for order ORD-1005 for Rs 15000'")
    print("-----------------------------------------------------------------")

    query_b = "Please process refund for order ORD-1005 for Rs 15000"
    at.chat_input[0].set_value(query_b).run(timeout=60)
    assert len(at.exception) == 0, f"Exceptions on Scenario B: {[e.message for e in at.exception]}"

    # Verify Thread Paused at Interrupt
    ticket_b = at.session_state.tracked_threads[tid_a]
    print("Thread status after high-value refund query:", ticket_b["status"])
    assert ticket_b["status"] == "pending_approval"
    assert ticket_b["interrupted"] is True
    assert ticket_b["dossier"]["amount"] == 15000.0

    # Verify Customer Portal shows Pending Notice
    msgs_b = at.session_state.messages_by_thread[tid_a]
    pending_msg = msgs_b[-1]
    assert pending_msg.get("pending_approval") is True
    print("Customer pending approval message rendered:\n", pending_msg["content"])

    # Verify Supervisor Queue has ticket
    approve_btns = [b for b in at.button if b.key and b.key.startswith("btn_approve_")]
    assert len(approve_btns) >= 1, "Approval button must appear in Approval Queue"
    reject_btns = [b for b in at.button if b.key and b.key.startswith("btn_reject_")]
    assert len(reject_btns) >= 1, "Reject button must appear in Approval Queue"
    print(f"Found {len(approve_btns)} ticket(s) awaiting approval in Supervisor Command Center.")

    # Supervisor approves the refund
    print("Supervisor clicking 'Approve Refund'...")
    approve_btns[0].click().run(timeout=60)
    assert len(at.exception) == 0, f"Exceptions on supervisor approval: {[e.message for e in at.exception]}"

    # Verify Thread resumed and approved
    ticket_b_post = at.session_state.tracked_threads[tid_a]
    assert ticket_b_post["status"] == "approved"
    assert ticket_b_post["interrupted"] is False
    assert "approve" in ticket_b_post["last_answer"].lower()
    print("Supervisor approval processed! Final answer:\n", ticket_b_post["last_answer"])

    # Verify DB State
    order_b = get_order("ORD-1005")
    assert order_b["status"] == "refunded"
    refunds_b = get_refunds_for_order("ORD-1005")
    assert len(refunds_b) == 1
    assert refunds_b[0]["amount"] == 15000.0
    assert refunds_b[0]["approved_by"] == "sup_lead_01"
    print(f"PASS: Order ORD-1005 refunded by supervisor {refunds_b[0]['approved_by']} (Amount: Rs {refunds_b[0]['amount']})")

    # Verify Customer Message History was updated with supervisor approval
    updated_customer_msgs = at.session_state.messages_by_thread[tid_a]
    assert "approve" in updated_customer_msgs[-1]["content"].lower()
    print("PASS: Customer View updated with supervisor approval confirmation!")

    # =========================================================================
    # SCENARIO C: Abusive Message (Direct Human Handoff)
    # =========================================================================
    print("\n-----------------------------------------------------------------")
    print("[Scenario C] Testing Abusive Message (Human Support Handoff)")
    print("-----------------------------------------------------------------")

    # Click New Chat for a fresh thread
    new_chat_btn = next((b for b in at.button if "New Chat" in b.label), None)
    assert new_chat_btn is not None
    new_chat_btn.click().run(timeout=60)
    assert len(at.exception) == 0

    tid_c = at.session_state.thread_id
    assert tid_c != tid_a, "New Chat must have generated a new thread_id"
    print(f"Started new chat with thread_id: {tid_c}")

    query_c = "You stupid useless bot refund my money right now or I will destroy your company you idiot"
    at.chat_input[0].set_value(query_c).run(timeout=60)
    assert len(at.exception) == 0, f"Exceptions on Scenario C: {[e.message for e in at.exception]}"

    ticket_c = at.session_state.tracked_threads[tid_c]
    assert ticket_c["status"] == "escalated"
    assert ticket_c["sentiment"] == "abusive"
    assert ticket_c["priority"] in ["High", "Critical"]
    assert ticket_c["dossier"] is not None
    print("Escalation Handled! Response:\n", ticket_c["last_answer"])
    print(f"PASS: Abusive message escalated to human handoff (Sentiment: {ticket_c['sentiment']}, Priority: {ticket_c['priority']})")

    # =========================================================================
    # SCENARIO D: PII Redaction Live Feed Verification
    # =========================================================================
    print("\n-----------------------------------------------------------------")
    print("[Scenario D] Testing PII Masking & Live Feed")
    print("Query: 'Contact me at secret_support@example.com or call +91 9876543210'")
    print("-----------------------------------------------------------------")

    query_d = "Contact me at secret_support@example.com or call +91 9876543210"
    at.chat_input[0].set_value(query_d).run(timeout=60)
    assert len(at.exception) == 0, f"Exceptions on Scenario D: {[e.message for e in at.exception]}"

    pii_feed = at.session_state.pii_feed
    print(f"PII feed items logged: {len(pii_feed)}")
    assert len(pii_feed) >= 2, "Expected at least 2 PII detections (email and phone)"
    pii_types = [item["type"] for item in pii_feed]
    assert "EMAIL" in pii_types
    assert "PHONE" in pii_types
    print(f"PASS: PII redacted and logged to feed ({pii_types})")

    # =========================================================================
    # SCENARIO E: Metrics & Audit Log Consistency Verification
    # =========================================================================
    print("\n-----------------------------------------------------------------")
    print("[Scenario E] Verifying Metrics Match SQLite Audit Log")
    print("-----------------------------------------------------------------")

    audit_logs = get_audit_logs(limit=200)
    print(f"Total audit log entries recorded in database: {len(audit_logs)}")
    assert len(audit_logs) >= 3, "Expected at least 3 audit log entries"

    # 1. Policy gate checks in audit log
    policy_checks = [l for l in audit_logs if l["action"] == "check_refund_policy"]
    print(f"Audit log check_refund_policy entries: {len(policy_checks)}")
    assert len(policy_checks) >= 2, "Expected policy checks for ORD-1001 and ORD-1005"

    # 2. Executed refunds in audit log
    refund_logs = [l for l in audit_logs if l["action"] == "execute_refund"]
    print(f"Audit log execute_refund entries: {len(refund_logs)}")
    assert len(refund_logs) == 2, f"Expected exactly 2 refunds executed, found {len(refund_logs)}"

    auto_execs = [l for l in refund_logs if "system_auto" in l["input"]]
    assert len(auto_execs) == 1, "Expected 1 auto refund log"
    sup_execs = [l for l in refund_logs if "sup_lead_01" in l["input"]]
    assert len(sup_execs) == 1, "Expected 1 supervisor refund log"

    # 3. Check UI Metrics
    metrics_dict = {m.label: m.value for m in at.metric}
    print("Rendered UI Metrics:", metrics_dict)
    assert int(metrics_dict["Active Tickets"]) >= 1
    assert int(metrics_dict["PII Redactions"]) >= 2
    assert "Auto-Resolved vs Escalated" in metrics_dict

    # =========================================================================
    # SCENARIO F: Reset Demo Button Verification
    # =========================================================================
    print("\n-----------------------------------------------------------------")
    print("[Scenario F] Testing Reset Demo Button")
    print("-----------------------------------------------------------------")
    reset_btn = next((b for b in at.button if "Reset Demo" in b.label), None)
    assert reset_btn is not None
    reset_btn.click().run(timeout=60)
    assert len(at.exception) == 0

    # Verify fresh state
    assert len(at.session_state.tracked_threads) == 0
    assert len(at.session_state.pii_feed) == 0
    order_fresh = get_order("ORD-1001")
    assert order_fresh["status"] == "delivered", "Database must be reseeded back to 'delivered'"
    print("PASS: Reset Demo button re-seeded database and cleared threads cleanly!")

    print("\n=================================================================")
    print("ALL 6 TEST SCENARIOS PASSED WITH ZERO CONSOLE EXCEPTIONS!")
    print("=================================================================")


if __name__ == "__main__":
    run_full_headless_verification()
