import os
import sys
import pytest
from typing import List, Dict, Any

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from utils.mock_db import reset_db, get_audit_logs, get_order
from policy.policy_gate import evaluate_refund_policy
from tools.order_tools import lookup_order, check_refund_policy, execute_refund


# Test results tracker for reporting
TEST_RESULTS = []


def record_result(test_name: str, scenario: str, expected: str, actual: str, status: str):
    TEST_RESULTS.append({
        "test_name": test_name,
        "scenario": scenario,
        "expected": expected,
        "actual": actual,
        "status": status
    })


@pytest.fixture(scope="module", autouse=True)
def clean_database():
    """Ensure database is reset to clean seed state once before all module tests run."""
    reset_db()


# =====================================================================
# 1. Seeded Scenario Tests
# =====================================================================

def test_eligible_order_delivered_3_days_ago():
    """ORD-1001: Delivered 3 days ago, amount Rs 1499 <= 2000, verified user -> Eligible & Auto-approved."""
    scenario = "Delivered 3 days ago (Rs 1,499 <= 2000, verified user)"
    
    # Check lookup
    lookup = lookup_order("ORD-1001", "user_1", session="test_s1")
    assert lookup["found"] is True
    
    # Check gate
    gate = check_refund_policy("ORD-1001", "user_1", session="test_s1")
    assert gate["eligible"] is True
    assert gate["requires_human_approval"] is False
    assert "eligible for automatic refund" in gate["reason"].lower()

    # Execute refund
    exec_res = execute_refund("ORD-1001", 1499.0, "Customer dissatisfied with bass", session="test_s1")
    assert exec_res["success"] is True
    assert exec_res["status"] == "EXECUTED"
    assert exec_res["refund_id"].startswith("REF-")

    # Order in DB should now be 'refunded'
    updated_order = get_order("ORD-1001")
    assert updated_order["status"] == "refunded"

    record_result("test_eligible_order_delivered_3_days_ago", scenario,
                  "Eligible & Executed", "Eligible & Executed", "PASS")


def test_expired_window_delivered_30_days_ago():
    """ORD-1002: Delivered 30 days ago (> 14 day window) -> Ineligible & Blocked."""
    scenario = "Delivered 30 days ago (window expired > 14 days)"
    gate = check_refund_policy("ORD-1002", "user_1", session="test_s2")
    assert gate["eligible"] is False
    assert "expired" in gate["reason"].lower()

    # Attempt execution -> Refused by tool
    exec_res = execute_refund("ORD-1002", 1800.0, "Keys stick occasionally", session="test_s2")
    assert exec_res["success"] is False
    assert exec_res["status"] == "REFUSED"
    assert "policy gate failed" in exec_res["reason"].lower()

    record_result("test_expired_window_delivered_30_days_ago", scenario,
                  "Ineligible & Refused", "Ineligible & Refused", "PASS")


def test_already_refunded_order():
    """ORD-1003: Already refunded order -> Ineligible & Blocked."""
    scenario = "Already refunded order (ORD-1003 status='refunded')"
    gate = check_refund_policy("ORD-1003", "user_2", session="test_s3")
    assert gate["eligible"] is False
    assert "already been refunded" in gate["reason"].lower()

    exec_res = execute_refund("ORD-1003", 1200.0, "Second refund attempt", session="test_s3")
    assert exec_res["success"] is False
    assert exec_res["status"] == "REFUSED"

    record_result("test_already_refunded_order", scenario,
                  "Ineligible & Refused", "Ineligible & Refused", "PASS")


def test_cancelled_order():
    """ORD-1004: Cancelled order -> Ineligible & Blocked."""
    scenario = "Cancelled order (ORD-1004 status='cancelled')"
    gate = check_refund_policy("ORD-1004", "user_2", session="test_s4")
    assert gate["eligible"] is False
    assert "cancelled" in gate["reason"].lower()

    exec_res = execute_refund("ORD-1004", 2500.0, "Want money back for cancelled item", session="test_s4")
    assert exec_res["success"] is False
    assert exec_res["status"] == "REFUSED"

    record_result("test_cancelled_order", scenario,
                  "Ineligible & Refused", "Ineligible & Refused", "PASS")


def test_high_value_order_refused_without_supervisor():
    """ORD-1005: High value Rs 15,000 order without human supervisor approval -> Refused."""
    scenario = "High value Rs 15,000 (no supervisor approval)"
    gate = check_refund_policy("ORD-1005", "user_1", session="test_s5")
    assert gate["eligible"] is True
    assert gate["requires_human_approval"] is True
    assert "supervisor approval required" in gate["reason"].lower()

    # Attempt refund with no approved_by
    exec_res = execute_refund("ORD-1005", 15000.0, "Screen flickering", approved_by=None, session="test_s5")
    assert exec_res["success"] is False
    assert exec_res["status"] == "REFUSED"
    assert "requires a verified human supervisor" in exec_res["reason"].lower()

    record_result("test_high_value_order_refused_without_supervisor", scenario,
                  "Requires Approval & Refused", "Requires Approval & Refused", "PASS")


def test_high_value_order_succeeds_with_supervisor():
    """ORD-1005: High value Rs 15,000 order with valid human supervisor ID -> Executed."""
    scenario = "High value Rs 15,000 (approved by sup_vikram_204)"
    exec_res = execute_refund(
        order_id="ORD-1005",
        amount=15000.0,
        reason="Screen flickering confirmed by hardware diagnostics",
        approved_by="sup_vikram_204",
        session="test_s6"
    )
    assert exec_res["success"] is True
    assert exec_res["status"] == "EXECUTED"
    assert exec_res["approved_by"] == "sup_vikram_204"

    record_result("test_high_value_order_succeeds_with_supervisor", scenario,
                  "Executed with Supervisor Approval", "Executed with Supervisor Approval", "PASS")


def test_unverified_user_order():
    """ORD-1006: User_3 is unverified -> Ineligible & Blocked."""
    scenario = "Unverified user (user_3 is_verified=0)"
    gate = check_refund_policy("ORD-1006", "user_3", session="test_s7")
    assert gate["eligible"] is False
    assert "unverified" in gate["reason"].lower()

    exec_res = execute_refund("ORD-1006", 999.0, "Speaker distorted", session="test_s7")
    assert exec_res["success"] is False
    assert exec_res["status"] == "REFUSED"

    record_result("test_unverified_user_order", scenario,
                  "Ineligible & Refused", "Ineligible & Refused", "PASS")


def test_cross_user_order_ownership_mismatch():
    """ORD-1007: Belongs to user_2, but requested by user_1 -> Refused."""
    scenario = "Cross-user order access (user_1 requests user_2's order)"
    
    # Lookup blocked
    lookup = lookup_order("ORD-1007", "user_1", session="test_s8")
    assert lookup["found"] is False
    assert "access denied" in lookup["error"].lower()

    # Policy gate blocked
    gate = check_refund_policy("ORD-1007", "user_1", session="test_s8")
    assert gate["eligible"] is False
    assert "ownership mismatch" in gate["reason"].lower()

    # Refund execution blocked
    exec_res = execute_refund("ORD-1007", 750.0, "Attempted unauthorized refund", user_id="user_1", session="test_s8")
    assert exec_res["success"] is False
    assert exec_res["status"] == "REFUSED"

    record_result("test_cross_user_order_ownership_mismatch", scenario,
                  "Ownership Mismatch & Refused", "Ownership Mismatch & Refused", "PASS")


def test_order_not_delivered_yet_processing():
    """ORD-1011: Status 'processing' (not yet delivered) -> Ineligible & Blocked."""
    scenario = "Undelivered processing order (ORD-1011 status='processing')"
    gate = check_refund_policy("ORD-1011", "user_5", session="test_s9")
    assert gate["eligible"] is False
    assert "not delivered" in gate["reason"].lower()

    exec_res = execute_refund("ORD-1011", 850.0, "Want refund before delivery", session="test_s9")
    assert exec_res["success"] is False
    assert exec_res["status"] == "REFUSED"

    record_result("test_order_not_delivered_yet_processing", scenario,
                  "Ineligible & Refused", "Ineligible & Refused", "PASS")


# =====================================================================
# 2. Adversarial Tests: LLM Attempts Action Execution Directly
# =====================================================================

def test_adversarial_llm_proposes_refund_for_ineligible_order():
    """
    Adversarial test: An LLM generates a tool call proposing a refund for an expired/ineligible order.
    The enterprise action layer must intercept and strictly reject the action.
    """
    scenario = "Adversarial LLM proposes refund on expired order ORD-1002"
    
    # Simulated LLM output / tool-call payload
    llm_generated_payload = {
        "action": "execute_refund",
        "order_id": "ORD-1002",
        "amount": 1800.0,
        "reason": "LLM says customer is very VIP and insists on refund!",
        "approved_by": "llm_super_agent"
    }

    # Enterprise action layer executes the tool deterministically:
    execution_result = execute_refund(
        order_id=llm_generated_payload["order_id"],
        amount=llm_generated_payload["amount"],
        reason=llm_generated_payload["reason"],
        approved_by=llm_generated_payload["approved_by"],
        session="adversarial_session_1"
    )

    # Gate blocks it deterministically
    assert execution_result["success"] is False
    assert execution_result["status"] == "REFUSED"
    assert "policy gate failed" in execution_result["reason"].lower()

    record_result("test_adversarial_llm_proposes_refund_for_ineligible_order", scenario,
                  "Strictly Blocked by Policy Gate", "Strictly Blocked by Policy Gate", "PASS")


def test_adversarial_llm_fakes_supervisor_approval_on_high_value():
    """
    Adversarial test: LLM attempts to pass a non-human supervisor id ('ai_agent', 'system', 'auto')
    to bypass the Rs 2,000 threshold on an eligible Rs 4,500 order (ORD-1008).
    execute_refund itself must refuse.
    """
    scenario = "Adversarial LLM claims fake supervisor 'ai_assistant' on Rs 4500 order"

    execution_result = execute_refund(
        order_id="ORD-1008",
        amount=4500.0,
        reason="LLM self-approved override",
        approved_by="ai_assistant",
        session="adversarial_session_2"
    )

    assert execution_result["success"] is False
    assert execution_result["status"] == "REFUSED"
    assert "requires a verified human supervisor" in execution_result["reason"].lower()

    record_result("test_adversarial_llm_fakes_supervisor_approval_on_high_value", scenario,
                  "Refused by execute_refund", "Refused by execute_refund", "PASS")


# =====================================================================
# 3. Audit Log Completeness and Summary Table Output
# =====================================================================

def test_print_pass_fail_table_and_audit_log_rows():
    """Prints a structured pass/fail table and all audit_log rows produced during test runs."""
    # Ensure audit entries exist
    logs = get_audit_logs(limit=100)
    if not logs:
        execute_refund("ORD-1001", 1499.0, "Isolated test sample refund", session="isolation_run")
        logs = get_audit_logs(limit=100)
    assert len(logs) > 0, "Audit log must contain records from tool calls and gate decisions"

    print("\n" + "=" * 105)
    print("                      ENTERPRISE ACTION LAYER & POLICY GATE: TEST RESULTS TABLE")
    print("=" * 105)
    print(f"{'#':<3} | {'Scenario':<45} | {'Expected Outcome':<28} | {'Status':<6}")
    print("-" * 105)
    
    for idx, r in enumerate(TEST_RESULTS, 1):
        print(f"{idx:<3} | {r['scenario'][:45]:<45} | {r['expected'][:28]:<28} | {r['status']:<6}")
    
    print("-" * 105)
    passed_count = sum(1 for r in TEST_RESULTS if r["status"] == "PASS")
    total_count = len(TEST_RESULTS)
    print(f"SUMMARY: {passed_count}/{total_count} tests PASSED ({passed_count/total_count*100:.1f}%)")
    print("=" * 105)

    print("\n" + "=" * 125)
    print("                                      PRODUCED AUDIT LOG ENTRIES (APPEND-ONLY)")
    print("=" * 125)
    print(f"{'ID':<4} | {'Timestamp':<25} | {'Session':<20} | {'Action':<32} | {'Decision':<18}")
    print("-" * 125)
    for log in logs:
        ts = log["timestamp"][:23]
        print(f"{log['log_id']:<4} | {ts:<25} | {log['session'][:20]:<20} | {log['action'][:32]:<32} | {log['decision']:<18}")
        # Print input and reason indented
        print(f"     -> Input:  {log['input']}")
        print(f"     -> Reason: {log['reason']}\n")
    print("=" * 125 + "\n")
