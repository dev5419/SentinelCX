"""Offline endpoint tests: real SSE flow and registry, controlled graph results."""
import ast
import asyncio
import json
import queue
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Literal, AsyncGenerator
import unittest
from unittest.mock import Mock

import test_redteam_sandbox as sandbox_tests
import test_semantic_security as security_tests


class Payload:
    def __init__(self, **values):
        self.values = values

    def model_dump(self):
        return self.values


class HumanReviewQueueTests(unittest.TestCase):
    setUp = sandbox_tests.SandboxTests.setUp

    def make_namespace(self, state, events=(), next_nodes=(), tasks=()):
        snapshot = SimpleNamespace(values=state, next=next_nodes, tasks=tasks)
        graph = SimpleNamespace(invoke=Mock(return_value=state), get_state=Mock(return_value=snapshot),
                                stream=Mock(return_value=iter(events)))
        ns = {"Dict": Dict, "Any": Any, "List": List, "Optional": Optional, "Literal": Literal,
              "AsyncGenerator": AsyncGenerator, "datetime": datetime, "timezone": timezone,
              "timedelta": timedelta, "uuid": uuid, "time": time, "json": json, "queue": queue,
              "threading": threading, "asyncio": asyncio, "graph": graph,
              "GraphInterrupt": type("GraphInterrupt", (Exception,), {}),
              "get_user": self.db.get_user, "get_orders_for_user": self.db.get_orders_for_user,
              "mask_pii": self.pii.mask_pii, "PENDING_APPROVALS": {}, "ACTIVE_TICKETS": {},
              "APPROVAL_HISTORY": [], "PII_AUDIT_FEED": [], "DEMO_USER_IDS": ("user_1", "user_2", "user_3"),
              "ChatRequest": object, "ChatResponse": Payload, "UserProfile": Payload,
              "Query": lambda default, **kwargs: default,
              "StreamingResponse": lambda iterator, **kwargs: iterator,
              "_prepare_chat_input": lambda thread, query, user, session, mode, order:
                  {"user_query": query, "user_id": user, "selected_order_id": order}}
        for name in ["_sanitize_for_export", "_register_human_review", "list_approvals", "list_tickets", "chat_turn"]:
            security_tests.function_from("api/server.py", name, ns)
        tree = ast.parse((sandbox_tests.ROOT / "api/server.py").read_text(encoding="utf-8"))
        node = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "chat_stream")
        node.decorator_list = []
        exec(compile(ast.Module(body=[node], type_ignores=[]), "api/server.py", "exec"), ns)
        return ns

    def rest(self, ns, thread="thread_aaaa", query="Review this order"):
        return ns["chat_turn"](SimpleNamespace(thread_id=thread, user_id="user_1", user_query=query,
                                               session_id=None, conversation_mode="order", selected_order_id="ORD-1013"))

    def stream(self, ns):
        async def run():
            iterator = await ns["chat_stream"]("thread_aaaa", "Review this order", "user_1", None, "order", "ORD-1013")
            events = []
            async for event in iterator:
                kind, data = event.strip().split("\ndata: ", 1)
                events.append((kind.removeprefix("event: "), json.loads(data)))
                if kind == "event: interrupt" or kind == "event: complete":
                    self.assertIn("thread_aaaa", ns["PENDING_APPROVALS"])
                    self.assertEqual(ns["ACTIVE_TICKETS"]["thread_aaaa"]["status"], "pending_approval")
            self.assertFalse(any(kind == "error" for kind, data in events), events)
            return events
        return asyncio.run(run())

    def test_rest_escalations_are_visible_unique_and_sanitized(self):
        ns = self.make_namespace({"action": "escalate", "extracted_order_id": "ORD-1013", "amount_at_risk": 599})
        first = self.rest(ns, query="Call alice@example.com")
        second = self.rest(ns, "thread_aaab")
        self.assertNotEqual(first["pending_approval_id"], second["pending_approval_id"])
        self.assertEqual(len(ns["list_approvals"]("pending")), 2)
        self.assertEqual(len(ns["list_tickets"]("pending_approval", None, 50)), 2)
        self.assertNotIn("alice@example.com", json.dumps(ns["PENDING_APPROVALS"]))
        repeat = self.rest(ns)
        self.assertEqual(first["pending_approval_id"], repeat["pending_approval_id"])
        self.assertEqual(len(ns["PENDING_APPROVALS"]), 2)

    def test_rest_low_value_reason_review_publishes_dossier(self):
        payload = {"dossier": {"issue_summary": "Billing discrepancy"}, "why_decision": {"final_route": "hitl_approval"}}
        ns = self.make_namespace({"action": "answer", "extracted_order_id": "ORD-1013", "amount_at_risk": 599,
                             "__interrupt__": (SimpleNamespace(value=payload),)})
        result = self.rest(ns)
        self.assertTrue(result["is_pending_approval"])
        self.assertEqual(result["action"], "hitl_interrupt")
        self.assertNotIn("2,000", result["answer"])
        self.assertEqual(ns["PENDING_APPROVALS"]["thread_aaaa"]["dossier"], payload["dossier"])

    def test_stream_interrupt_survives_missing_snapshot_next(self):
        state = {"action": "answer", "extracted_order_id": "ORD-1013", "amount_at_risk": 599}
        payload = {"message": "Reason requires review", "dossier": {"issue_summary": "Billing issue"}}
        ns = self.make_namespace(state, [{"triage": state}, {"__interrupt__": (SimpleNamespace(value=payload),)}])
        events = self.stream(ns)
        interrupt = next(data for kind, data in events if kind == "interrupt")
        complete = next(data for kind, data in events if kind == "complete")
        self.assertTrue(complete["is_pending_approval"])
        self.assertEqual(interrupt["approval_id"], complete["pending_approval_id"])
        self.assertEqual(ns["PENDING_APPROVALS"]["thread_aaaa"]["amount"], 599)
        self.assertEqual(ns["PENDING_APPROVALS"]["thread_aaaa"]["order_id"], "ORD-1013")

    def test_stream_plain_escalation_and_snapshot_only_interrupt(self):
        state = {"action": "escalate", "extracted_order_id": "ORD-1013", "amount_at_risk": 599}
        ns = self.make_namespace(state, [{"escalate": state}])
        self.stream(ns)
        self.assertEqual(ns["PENDING_APPROVALS"]["thread_aaaa"]["type"], "escalation")
        payload = {"dossier": {"issue_summary": "Reason review"}}
        state = {"action": "answer", "amount_at_risk": 599}
        tasks = (SimpleNamespace(interrupts=(SimpleNamespace(value=payload),)),)
        ns = self.make_namespace(state, tasks=tasks)
        self.stream(ns)
        item = ns["PENDING_APPROVALS"]["thread_aaaa"]
        self.assertEqual(item["type"], "refund_approval")
        self.assertEqual(item["order_id"], "ORD-1013")
        self.assertEqual(item["dossier"], payload["dossier"])

    def test_all_displayed_demo_customers_are_the_same_three(self):
        ns = self.make_namespace({})
        seed = security_tests.function_from("api/server.py", "_seed_initial_tickets_and_approvals", ns)
        seed()
        for registry in [ns["PENDING_APPROVALS"].values(), ns["ACTIVE_TICKETS"].values(), ns["APPROVAL_HISTORY"]]:
            for item in registry:
                self.assertIn(item["user_id"], ns["DEMO_USER_IDS"])
                self.assertEqual(item["user_name"], self.db.get_user(item["user_id"])["name"])
        users = security_tests.function_from("api/server.py", "get_demo_users", ns)()
        self.assertEqual([user["name"] for user in users], ["Alice Johnson", "Bob Smith", "Charlie Davis"])


if __name__ == "__main__":
    unittest.main()
