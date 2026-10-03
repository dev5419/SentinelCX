import os
import sys
import pytest
from typing import List, Dict, Any

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from agents.triage_agent import triage_agent
from core.graph import build_graph, route_from_triage
from core.state import SupportState
from utils.mock_db import reset_db


@pytest.fixture(scope="module", autouse=True)
def init_db_fixture():
    reset_db()


# 20 labeled evaluation queries (English + Hinglish, covering all intents, sentiments, and overrides)
LABELED_DATA = [
    # 1. FAQ English
    {
        "id": 1,
        "query": "What is your return policy window for delivered items?",
        "expected_intents": ["faq"],
        "expected_sentiments": ["neutral"],
        "expected_priorities": ["Low"],
        "expected_transactional": False,
        "expected_order_id": None
    },
    # 2. FAQ Hinglish
    {
        "id": 2,
        "query": "Aapke store par delivery kitne din me hoti hai?",
        "expected_intents": ["faq"],
        "expected_sentiments": ["neutral"],
        "expected_priorities": ["Low"],
        "expected_transactional": False,
        "expected_order_id": None
    },
    # 3. Refund Request English (with order ID)
    {
        "id": 3,
        "query": "I would like to request a refund for order ORD-1001",
        "expected_intents": ["refund_request"],
        "expected_sentiments": ["neutral", "frustrated"],
        "expected_priorities": ["Medium", "Low"],
        "expected_transactional": True,
        "expected_order_id": "ORD-1001"
    },
    # 4. Refund Request Hinglish (with order ID)
    {
        "id": 4,
        "query": "Bhai mera order ORD-501 abhi tak deliver nahi hua mujhe refund chahiye",
        "expected_intents": ["refund_request"],
        "expected_sentiments": ["frustrated", "neutral"],
        "expected_priorities": ["Medium", "High"],
        "expected_transactional": True,
        "expected_order_id": "ORD-501"
    },
    # 5. Billing Dispute English
    {
        "id": 5,
        "query": "I was charged twice on my credit card for the same transaction",
        "expected_intents": ["billing_dispute"],
        "expected_sentiments": ["frustrated", "neutral"],
        "expected_priorities": ["High", "Medium"],
        "expected_transactional": True,
        "expected_order_id": None
    },
    # 6. Billing Dispute Hinglish
    {
        "id": 6,
        "query": "Mera double payment kat gaya hai ek hi order ke liye do baar paise kate",
        "expected_intents": ["billing_dispute"],
        "expected_sentiments": ["frustrated", "neutral"],
        "expected_priorities": ["High", "Medium"],
        "expected_transactional": True,
        "expected_order_id": None
    },
    # 7. Login English
    {
        "id": 7,
        "query": "I forgot my password and cannot sign in to my account",
        "expected_intents": ["login"],
        "expected_sentiments": ["neutral"],
        "expected_priorities": ["Medium", "Low"],
        "expected_transactional": False,
        "expected_order_id": None
    },
    # 8. Login Hinglish
    {
        "id": 8,
        "query": "Mera account login nahi ho raha hai password reset link bhejo please",
        "expected_intents": ["login"],
        "expected_sentiments": ["neutral"],
        "expected_priorities": ["Medium", "Low"],
        "expected_transactional": False,
        "expected_order_id": None
    },
    # 9. Subscription English
    {
        "id": 9,
        "query": "How do I cancel my monthly subscription renewal before next billing cycle?",
        "expected_intents": ["subscription"],
        "expected_sentiments": ["neutral"],
        "expected_priorities": ["Medium", "Low"],
        "expected_transactional": True,
        "expected_order_id": None
    },
    # 10. Subscription Hinglish
    {
        "id": 10,
        "query": "Agle mahine ka subscription renew nahi karna please cancel kardo",
        "expected_intents": ["subscription"],
        "expected_sentiments": ["neutral"],
        "expected_priorities": ["Medium", "Low"],
        "expected_transactional": True,
        "expected_order_id": None
    },
    # 11. Unknown / General English
    {
        "id": 11,
        "query": "Hello, I have a general inquiry about your services",
        "expected_intents": ["unknown", "faq"],
        "expected_sentiments": ["neutral"],
        "expected_priorities": ["Low"],
        "expected_transactional": False,
        "expected_order_id": None
    },
    # 12. Unknown / General Hinglish
    {
        "id": 12,
        "query": "Mujhe kuch baat karni hai support agent se general issue par",
        "expected_intents": ["unknown", "faq"],
        "expected_sentiments": ["neutral"],
        "expected_priorities": ["Low", "Medium"],
        "expected_transactional": False,
        "expected_order_id": None
    },
    # 13. Positive Sentiment English
    {
        "id": 13,
        "query": "Thank you so much! Great service, just wanted to ask how to check past invoices",
        "expected_intents": ["faq", "billing_dispute"],
        "expected_sentiments": ["positive"],
        "expected_priorities": ["Low"],
        "expected_transactional": False,
        "expected_order_id": None
    },
    # 14. Abusive Sentiment Override (English -> Priority >= High)
    {
        "id": 14,
        "query": "You idiot scammers, your useless service stole my money and you are completely incompetent!",
        "expected_intents": ["billing_dispute", "refund_request", "unknown"],
        "expected_sentiments": ["abusive"],
        "expected_priorities": ["High", "Critical"],
        "expected_transactional": True,
        "expected_order_id": None
    },
    # 15. Abusive Sentiment Override (Hinglish -> Priority >= High)
    {
        "id": 15,
        "query": "Tum sab chor ho kutte, bakwas service hai meri paise wapas karo nahi toh dekh lena",
        "expected_intents": ["refund_request", "billing_dispute", "unknown"],
        "expected_sentiments": ["abusive"],
        "expected_priorities": ["High", "Critical"],
        "expected_transactional": True,
        "expected_order_id": None
    },
    # 16. Legal Keyword Override (court/lawyer/fraud -> Priority >= High)
    {
        "id": 16,
        "query": "I will consult my lawyer and take legal action in consumer court against your fraud company",
        "expected_intents": ["billing_dispute", "refund_request", "unknown"],
        "expected_sentiments": ["frustrated", "neutral"],
        "expected_priorities": ["High", "Critical"],
        "expected_transactional": True,
        "expected_order_id": None
    },
    # 17. Police / FIR Keyword Override (police/FIR -> Priority >= High)
    {
        "id": 17,
        "query": "Agar mera paisa nahi aaya toh mai police station me FIR darj karwaunga cyber cell me",
        "expected_intents": ["refund_request", "billing_dispute", "unknown"],
        "expected_sentiments": ["frustrated", "neutral"],
        "expected_priorities": ["High", "Critical"],
        "expected_transactional": True,
        "expected_order_id": None
    },
    # 18. Chargeback Keyword Override (chargeback -> Priority >= High)
    {
        "id": 18,
        "query": "I am filing an immediate bank chargeback for this fraudulent unauthorized transaction",
        "expected_intents": ["billing_dispute", "refund_request"],
        "expected_sentiments": ["frustrated", "neutral"],
        "expected_priorities": ["High", "Critical"],
        "expected_transactional": True,
        "expected_order_id": None
    },
    # 19. Amount-at-Risk Override > 10,000 -> Critical (Rs 15,000)
    {
        "id": 19,
        "query": "My order ORD-1005 for Rs 15000 has not arrived and I need immediate resolution",
        "expected_intents": ["refund_request"],
        "expected_sentiments": ["frustrated", "neutral"],
        "expected_priorities": ["Critical"],
        "expected_transactional": True,
        "expected_order_id": "ORD-1005"
    },
    # 20. Amount-at-Risk Override > 10,000 -> Critical (Rs 25,000)
    {
        "id": 20,
        "query": "Maine Rs 25000 ka order kiya tha par parcel deliver nahi hua, itna bada amount at risk hai",
        "expected_intents": ["refund_request"],
        "expected_sentiments": ["frustrated", "neutral"],
        "expected_priorities": ["Critical"],
        "expected_transactional": True,
        "expected_order_id": None
    }
]


def test_triage_20_labeled_queries():
    """Runs all 20 labeled queries and reports accuracy per field."""
    results = []
    sample_outputs = []

    for item in LABELED_DATA:
        state = {"user_query": item["query"]}
        out = triage_agent(state)

        # Accuracy checks
        intent_match = (out["intent"] in item["expected_intents"])
        sentiment_match = (out["sentiment"] in item["expected_sentiments"])
        priority_match = (out["priority"] in item["expected_priorities"])
        trans_match = (out["is_transactional"] == item["expected_transactional"])

        order_match = True
        if item["expected_order_id"]:
            order_match = (out["extracted_order_id"] == item["expected_order_id"])

        results.append({
            "id": item["id"],
            "query": item["query"],
            "intent_match": intent_match,
            "sentiment_match": sentiment_match,
            "priority_match": priority_match,
            "trans_match": trans_match,
            "order_match": order_match,
            "output": out
        })

        if item["id"] in [3, 14, 19]:
            sample_outputs.append((item["id"], item["query"], out))

    total = len(results)
    intent_acc = sum(1 for r in results if r["intent_match"]) / total * 100
    sentiment_acc = sum(1 for r in results if r["sentiment_match"]) / total * 100
    priority_acc = sum(1 for r in results if r["priority_match"]) / total * 100
    trans_acc = sum(1 for r in results if r["trans_match"]) / total * 100
    order_acc = sum(1 for r in results if r["order_match"]) / total * 100

    print("\n" + "=" * 90)
    print("                     TRIAGE AGENT EVALUATION ACCURACY REPORT")
    print("=" * 90)
    print(f"Total Evaluated Queries:       {total}")
    print(f"Intent Classification Accuracy: {intent_acc:.1f}% ({sum(1 for r in results if r['intent_match'])}/{total})")
    print(f"Sentiment Detection Accuracy:   {sentiment_acc:.1f}% ({sum(1 for r in results if r['sentiment_match'])}/{total})")
    print(f"Priority (with Overrides) Acc:  {priority_acc:.1f}% ({sum(1 for r in results if r['priority_match'])}/{total})")
    print(f"Transactional Accuracy:         {trans_acc:.1f}% ({sum(1 for r in results if r['trans_match'])}/{total})")
    print(f"Order ID Extraction Accuracy:   {order_acc:.1f}% ({sum(1 for r in results if r['order_match'])}/{total})")
    print("=" * 90)

    print("\n" + "=" * 90)
    print("                           3 SAMPLE STRUCTURED OUTPUTS")
    print("=" * 90)
    for sample_id, q, out in sample_outputs:
        print(f"\n[Sample Query #{sample_id}]: \"{q}\"")
        for k, v in out.items():
            print(f"   {k:<20}: {v}")
    print("=" * 90 + "\n")

    # Assert accuracy thresholds
    assert intent_acc >= 85.0, f"Intent accuracy too low: {intent_acc}%"
    assert sentiment_acc >= 85.0, f"Sentiment accuracy too low: {sentiment_acc}%"
    assert priority_acc >= 85.0, f"Priority override accuracy too low: {priority_acc}%"
    assert trans_acc >= 85.0, f"Transactional accuracy too low: {trans_acc}%"
    assert order_acc >= 95.0, f"Order ID extraction accuracy too low: {order_acc}%"


def test_graph_compiles():
    """Validates that the updated graph with triage and policy nodes compiles cleanly."""
    graph = build_graph()
    assert graph is not None


def test_graph_routing_rules():
    """
    Tests that route_from_triage deterministically routes each category:
    - transactional -> policy path
    - faq / informational -> RAG path
    - abusive or Critical -> direct human handoff (escalate)
    - unknown low confidence -> clarify
    """
    # 1. Abusive sentiment -> escalate
    s_abusive = SupportState(
        sentiment="abusive",
        priority="High",
        is_transactional=False,
        intent="unknown",
        intent_confidence=0.5
    )
    assert route_from_triage(s_abusive) == "escalate"

    # 2. Critical priority -> escalate
    s_critical = SupportState(
        sentiment="neutral",
        priority="Critical",
        is_transactional=True,
        intent="refund_request",
        intent_confidence=0.9
    )
    assert route_from_triage(s_critical) == "escalate"

    # 3. Transactional (Medium/Low priority) -> policy
    s_transactional = SupportState(
        sentiment="neutral",
        priority="Medium",
        is_transactional=True,
        intent="refund_request",
        intent_confidence=0.95,
        extracted_order_id="ORD-1001"
    )
    assert route_from_triage(s_transactional) in ["policy", "policy_gate"]

    # 4. FAQ / Informational -> rag
    s_faq = SupportState(
        sentiment="neutral",
        priority="Low",
        is_transactional=False,
        intent="faq",
        intent_confidence=0.95
    )
    assert route_from_triage(s_faq) == "rag"

    # 5. Unknown with low confidence -> routes to RAG / clarify
    s_clarify = SupportState(
        sentiment="neutral",
        priority="Low",
        is_transactional=False,
        intent="unknown",
        intent_confidence=0.4
    )
    assert route_from_triage(s_clarify) in ["clarify", "rag"]
