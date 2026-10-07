"""Selected-order boundaries, follow-ups, and non-destructive demo migration."""
import re
import time
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_redteam_sandbox as sandbox_tests
import test_semantic_security as security_tests


class RequestError(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail


class OrderContextTests(unittest.TestCase):
    setUp = sandbox_tests.SandboxTests.setUp

    def prepare(self, query, mode="order", order="ORD-1001", previous=None, user="user_1"):
        namespace = {"get_user": self.db.get_user, "get_order": self.db.get_order,
                     "HTTPException": RequestError, "re": re,
                     "graph": SimpleNamespace(get_state=lambda config: SimpleNamespace(values=previous or {}))}
        function = security_tests.function_from("api/server.py", "_prepare_chat_input", namespace)
        return function("thread", query, user, "session", mode, order)

    def triage(self, query, intent, mode, order, previous=None, reason=None, category="unclear", confidence=0.0):
        obj = SimpleNamespace(intent=intent, intent_confidence=0.95, sentiment="neutral",
                              priority="Medium", is_transactional=intent == "refund_request",
                              extracted_order_id=None, amount_at_risk=None, refund_reason=reason,
                              refund_reason_category=category, refund_reason_confidence=confidence)
        namespace = {"Dict": dict, "Any": object, "mask_pii": self.pii.mask_pii,
                     "_call_llm_for_triage": Mock(return_value=obj), "_extract_amount_from_query": lambda query: None,
                     "ORDER_ID_REGEX": re.compile(r"\bORD-\d+\b", re.I),
                     "LEGAL_FRAUD_KEYWORDS": [], "ABUSIVE_KEYWORDS": [],
                     "datetime": datetime, "timezone": timezone, "timedelta": timedelta,
                     "SLA_DELTAS": {"Medium": timedelta(hours=4), "Critical": timedelta(minutes=15)},
                     "get_order": self.db.get_order, "re": re}
        namespace["_refund_reason_from_query"] = security_tests.function_from("agents/triage_agent.py", "_refund_reason_from_query", namespace)
        function = security_tests.function_from("agents/triage_agent.py", "triage_agent", namespace)
        return function({**(previous or {}), "user_query": query, "user_id": "user_1", "conversation_mode": mode,
                         "selected_order_id": order})

    def test_owned_order_and_followup_use_selected_id(self):
        result = self.prepare("Please refund this order")
        self.assertEqual(result["selected_order"]["order_id"], "ORD-1001")
        result = self.triage("Please refund this order", "refund_request", "order", "ORD-1001")
        self.assertEqual(result["extracted_order_id"], "ORD-1001")
        self.assertTrue(result["is_transactional"])
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["pending_refund_order_id"], "ORD-1001")

    def evaluate_request(self, state):
        namespace = {"SupportState": dict, "Dict": dict, "Any": object, "time": time,
                     "check_refund_policy": self.tools.check_refund_policy}
        return security_tests.function_from("core/graph.py", "policy_gate_node", namespace)(state)

    def test_refund_reason_followup_and_execution(self):
        first = self.triage("refund me the amount", "refund_request", "order", "ORD-1001")
        self.assertEqual(first["action"], "clarify")
        self.assertEqual(self.db.get_refunds_for_order("ORD-1001"), [])
        next_turn = self.triage("It arrived broken", "unknown", "order", "ORD-1001", first)
        self.assertEqual(next_turn["intent"], "refund_request")
        self.assertEqual(next_turn["refund_reason_category"], "damaged")
        self.assertIsNone(next_turn["pending_refund_order_id"])
        state = {**next_turn, "user_id": "user_1"}
        state.update(self.evaluate_request(state))
        self.assertTrue(state["policy_decision"]["eligible"])
        self.assertFalse(state["policy_decision"]["requires_human_approval"])
        execute = security_tests.function_from("core/graph.py", "auto_execute_node", {
            "SupportState": dict, "Dict": dict, "Any": object, "time": time,
            "execute_refund": self.tools.execute_refund, "get_order": self.db.get_order})
        result = execute(state)
        self.assertEqual(result["action"], "answer")
        self.assertEqual(self.db.get_refunds_for_order("ORD-1001")[0]["reason"], "arrived broken")

    def test_reason_gate_and_supervisor_review(self):
        state = {"extracted_order_id": "ORD-1001", "user_id": "user_1", "amount_at_risk": 1499}
        self.assertEqual(self.evaluate_request(state)["action"], "clarify")
        for category in ["missing_delivery", "billing_issue", "other", "unclear"]:
            result = self.evaluate_request({**state, "refund_reason": "Customer issue", "refund_reason_category": category})
            self.assertTrue(result["policy_decision"]["requires_human_approval"])
        expired = self.evaluate_request({**state, "extracted_order_id": "ORD-1002", "refund_reason": "arrived broken", "refund_reason_category": "damaged"})
        self.assertFalse(expired["policy_decision"]["eligible"])

    def test_vague_forged_unrelated_and_cancelled_reasons_do_not_resume(self):
        pending = {"pending_refund_order_id": "ORD-1001"}
        for text in ["yes", "please hurry", "refund it", "It is not damaged"]:
            result = self.triage(text, "refund_request", "order", "ORD-1001", pending,
                                 reason="arrived broken", category="damaged", confidence=0.99)
            self.assertEqual(result["action"], "clarify")
            self.assertIsNone(result["refund_reason"])
        faq = self.triage("What is the delivery policy?", "faq", "order", "ORD-1001", pending)
        self.assertFalse(faq["is_transactional"])
        cancelled = self.triage("Don't refund it, it is not working", "refund_request", "order", "ORD-1001", pending)
        self.assertFalse(cancelled["is_transactional"])
        self.assertIsNone(cancelled["pending_refund_order_id"])
        new_request = self.triage("refund me", "refund_request", "order", "ORD-1001",
                                  {"refund_reason": "arrived broken", "refund_reason_category": "damaged"})
        self.assertEqual(new_request["action"], "clarify")

    def test_grounded_semantic_reason_and_order_isolation(self):
        text = "Refund please, the screen flickers every few seconds"
        result = self.triage(text, "refund_request", "order", "ORD-1001",
                             reason="the screen flickers every few seconds", category="defective", confidence=0.95)
        self.assertEqual(result["refund_reason_category"], "defective")
        other_order = self.triage("It arrived broken", "unknown", "order", "ORD-1005",
                                  {"pending_refund_order_id": "ORD-1001"})
        self.assertFalse(other_order["is_transactional"])

    def test_order_policy_question_does_not_trigger_refund(self):
        result = self.triage("What is the refund policy for this order?", "faq", "order", "ORD-1005")
        self.assertEqual(result["extracted_order_id"], "ORD-1005")
        self.assertFalse(result["is_transactional"])

    def test_missing_and_foreign_order_have_same_response(self):
        errors = []
        for order in ["ORD-9999", "ORD-1007"]:
            with self.assertRaises(RequestError) as error:
                self.prepare("Refund this", order=order)
            errors.append((error.exception.status_code, error.exception.detail))
        self.assertEqual(errors[0], errors[1])
        self.assertEqual(errors[0][0], 404)

    def test_cannot_switch_orders_or_customers_in_thread(self):
        previous = {"user_id": "user_1", "conversation_mode": "order", "selected_order_id": "ORD-1001"}
        for mode, order, user in [("order", "ORD-1005", "user_1"), ("general", None, "user_1"),
                                  ("order", "ORD-1001", "user_2")]:
            with self.assertRaises(RequestError) as error:
                self.prepare("Help", mode, order, previous, user)
            self.assertEqual(error.exception.status_code, 409)
        with self.assertRaises(RequestError) as error:
            self.prepare("Refund ORD-1005", order="ORD-1001")
        self.assertEqual(error.exception.status_code, 422)

    def test_general_faq_and_transaction_boundaries(self):
        self.assertIsNone(self.prepare("What is the return window?", "general", None)["selected_order"])
        result = self.triage("Refund me please", "refund_request", "general", None)
        self.assertEqual(result["action"], "clarify")
        self.assertFalse(result["is_transactional"])
        with self.assertRaises(RequestError):
            self.prepare("Refund ORD-1001", "general", None)

    def test_alice_scenarios_exist_without_resetting_transactions(self):
        orders = self.db.get_orders_for_user("user_1")
        self.assertTrue({"delivered", "processing", "shipped", "refunded", "cancelled"} <= {o["status"] for o in orders})
        self.assertEqual(self.db.get_order("ORD-1002")["status"], "delivered")
        self.assertEqual(len(self.db.get_refunds_for_order("ORD-1054")), 1)

        refund = self.tools.execute_refund("ORD-1001", 1499, "test", user_id="user_1")
        self.assertTrue(refund["success"])
        self.db.init_db()
        self.assertEqual(self.db.get_order("ORD-1001")["status"], "refunded")
        self.assertEqual(len(self.db.get_refunds_for_order("ORD-1054")), 1)

    def test_consolidation_preserves_data_and_refund_ownership(self):
        with self.db.get_db() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 3)
            conn.executemany("INSERT INTO users VALUES (?,?,?,?)", [
                ("user_4", "Legacy verified", "legacy@example.com", 1),
                ("user_6", "Legacy unverified", "old@example.com", 0)])
            conn.execute("UPDATE orders SET user_id='user_4' WHERE order_id='ORD-1054'")
            conn.execute("UPDATE refunds SET user_id='user_4' WHERE order_id='ORD-1054'")
            conn.execute("UPDATE orders SET user_id='user_6' WHERE order_id='ORD-1026'")
            conn.execute("PRAGMA user_version=1")
            before = {table: [dict(row) for row in conn.execute(f'SELECT * FROM {table}')]
                      for table in ["orders", "refunds", "audit_log"]}
        self.db.init_db()
        with self.db.get_db() as conn:
            self.assertEqual({row[0] for row in conn.execute("SELECT user_id FROM users")}, {"user_1", "user_2", "user_3"})
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
            for table, rows in before.items():
                after = [dict(row) for row in conn.execute(f'SELECT * FROM {table}')]
                self.assertEqual([{k: v for k, v in row.items() if k != "user_id"} for row in rows],
                                 [{k: v for k, v in row.items() if k != "user_id"} for row in after])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM refunds r JOIN orders o ON o.order_id=r.order_id WHERE r.user_id != o.user_id").fetchone()[0], 0)
        self.assertEqual(self.db.get_order("ORD-1026")["user_id"], "user_3")
        self.assertEqual(self.db.get_order("ORD-1054")["user_id"], "user_1")


if __name__ == "__main__":
    unittest.main()
