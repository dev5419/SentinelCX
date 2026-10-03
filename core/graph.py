import time
import uuid
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from core.state import SupportState
from core.dossier import generate_handoff_dossier
from agents.pii_guard import mask_pii
from agents.injection_guard import check_injection
from utils.language import detect_language, normalize_to_english
from agents.triage_agent import triage_agent
from agents.grounding_guard import is_grounded
from config import LLM
from rag.retriever import get_retriever, retriever, retrieve_with_scores, build_citation, resolve_doc_path
from tools.order_tools import check_refund_policy, execute_refund
from utils.mock_db import get_order, log_audit


# ============================================================================
# 1. Pipeline Nodes with Trace Logging
# ============================================================================

def pii_node(state: SupportState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    raw_query = state.get("user_query", "")
    pii_res = mask_pii(raw_query)
    dur = round((time.perf_counter() - t0) * 1000, 2)

    counts = pii_res.get("counts", {})
    total_masked = sum(v for k, v in counts.items() if k != "total")
    summary = f"Masked {total_masked} PII items" if total_masked > 0 else "No PII detected"

    return {
        "sanitized_query": pii_res["sanitized_query"],
        "redacted_pii": pii_res["redacted_pii"],
        "pii_counts": counts,
        "action": "answer",
        "force_escalate": False,
        "trace": [{
            "node": "pii",
            "summary": summary,
            "duration_ms": dur
        }]
    }


def injection_node(state: SupportState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    sanitized = state.get("sanitized_query") or state.get("user_query", "")
    session_id = state.get("session_id", "default_session")

    injection_res = check_injection(sanitized, session=session_id)
    lang = state.get("language") or detect_language(sanitized)
    query_en = state.get("query_en") or normalize_to_english(sanitized, lang)

    dur = round((time.perf_counter() - t0) * 1000, 2)

    if injection_res["is_injection"]:
        dossier = generate_handoff_dossier(
            state=state,
            issue_summary=f"Security alert: Prompt injection detected ({injection_res['reason_code']})",
            proposed_action="Security hold & escalation"
        )
        return {
            "answer": injection_res["safe_message"],
            "action": "escalate",
            "force_escalate": True,
            "handoff_dossier": dossier,
            "language": lang,
            "query_en": query_en,
            "trace": [{
                "node": "injection",
                "summary": f"Prompt injection detected ({injection_res['reason_code']}), blocked safely",
                "duration_ms": dur
            }]
        }

    return {
        "language": lang,
        "query_en": query_en,
        "trace": [{
            "node": "injection",
            "summary": "Passed prompt injection and security validation",
            "duration_ms": dur
        }]
    }


def triage_node(state: SupportState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    triage_res = triage_agent(state)
    dur = round((time.perf_counter() - t0) * 1000, 2)

    summary = (
        f"Intent: {triage_res['intent']}, Sentiment: {triage_res['sentiment']}, "
        f"Priority: {triage_res['priority']}, Transactional: {triage_res['is_transactional']}"
    )
    if triage_res.get("extracted_order_id"):
        summary += f", Order: {triage_res['extracted_order_id']}"

    triage_res["trace"] = [{
        "node": "triage",
        "summary": summary,
        "duration_ms": dur
    }]
    return triage_res


def escalate_node(state: SupportState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    sentiment = state.get("sentiment", "neutral")
    priority = state.get("priority", "High")
    lang = state.get("language", "en")

    dossier = generate_handoff_dossier(
        state=state,
        issue_summary=f"Customer query flagged for escalation (sentiment={sentiment}, priority={priority})",
        proposed_action="Direct human support specialist handoff"
    )

    ans = (
        "Aapki request human support specialist ko escalate kar di gayi hai. Humari team jaldi aapse sampark karegi."
        if lang == "hinglish" else
        "Your request has been escalated to a human support specialist for immediate assistance. A ticket has been created."
    )
    dur = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "answer": ans,
        "action": "escalate",
        "force_escalate": True,
        "handoff_dossier": dossier,
        "trace": [{
            "node": "escalate",
            "summary": f"Escalated to human support: sentiment={sentiment}, priority={priority}",
            "duration_ms": dur
        }]
    }


def policy_gate_node(state: SupportState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    order_id = state.get("extracted_order_id")
    user_id = state.get("user_id", "user_1")
    session_id = state.get("session_id", "default_session")
    amount = state.get("amount_at_risk")
    lang = state.get("language", "en")

    # If transactional query lacks an order ID, ask for clarification
    if not order_id:
        msg = (
            "Kripya apna Order ID (jaise ORD-1001) provide karein taaki hum aapke order ki policy eligibility check kar sakein."
            if lang == "hinglish" else
            "Please provide your Order ID (e.g. ORD-1001) so we can verify policy eligibility and assist with your transaction."
        )
        dur = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "answer": msg,
            "action": "clarify",
            "trace": [{
                "node": "policy_gate",
                "summary": "Missing order ID in transactional request, requesting clarification",
                "duration_ms": dur
            }]
        }

    # Order ID present: evaluate policy gate
    policy_res = check_refund_policy(
        order_id=order_id,
        user_id=user_id,
        requested_amount=amount,
        session=session_id
    )

    tool_entry = [{
        "tool": "check_refund_policy",
        "input": {"order_id": order_id, "user_id": user_id, "amount": amount},
        "result": policy_res
    }]
    dur = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "policy_decision": policy_res,
        "tool_history": tool_entry,
        "trace": [{
            "node": "policy_gate",
            "summary": f"Policy evaluated for {order_id}: eligible={policy_res['eligible']}, requires_human_approval={policy_res['requires_human_approval']}",
            "duration_ms": dur
        }]
    }


def reject_node(state: SupportState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    policy = state.get("policy_decision", {})
    order_id = state.get("extracted_order_id", "ORDER")
    reason = policy.get("reason", "Refund not eligible under current policy.")
    quote = policy.get("policy_quote", "")
    lang = state.get("language", "en")

    if quote:
        ans = (
            f"Aapka request process nahi ho sakta: {reason}\n\nPolicy: \"{quote}\""
            if lang == "hinglish" else
            f"Your refund request for order {order_id} cannot be processed: {reason}\n\nPolicy: \"{quote}\""
        )
    else:
        ans = (
            f"Aapka request process nahi ho sakta: {reason}"
            if lang == "hinglish" else
            f"Your refund request for order {order_id} cannot be processed: {reason}"
        )

    dur = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "answer": ans,
        "action": "reject",
        "trace": [{
            "node": "reject",
            "summary": f"Rejected refund for {order_id}: {reason}",
            "duration_ms": dur
        }]
    }


def auto_execute_node(state: SupportState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    order_id = state.get("extracted_order_id")
    user_id = state.get("user_id", "user_1")
    session_id = state.get("session_id", "default_session")
    amount = state.get("amount_at_risk")
    lang = state.get("language", "en")

    if amount is None:
        order = get_order(order_id)
        amount = float(order.get("amount", 0.0)) if order else 0.0

    exec_res = execute_refund(
        order_id=order_id,
        amount=amount,
        reason="Customer refund request (auto-approved within policy)",
        approved_by="system_auto",
        user_id=user_id,
        session=session_id
    )

    tool_entry = [{
        "tool": "execute_refund",
        "input": {"order_id": order_id, "amount": amount, "approved_by": "system_auto"},
        "result": exec_res
    }]

    if exec_res.get("success"):
        refund_id = exec_res.get("refund_id")
        ans = (
            f"Aapke order {order_id} ka refund Rs {amount:.2f} safaltapoorvak process ho gaya hai. Refund ID: {refund_id}."
            if lang == "hinglish" else
            f"Your refund of Rs {amount:.2f} for order {order_id} has been automatically approved and processed successfully. Refund ID: {refund_id}."
        )
        action = "answer"
        summary = f"Auto-executed refund for {order_id} (Rs {amount:.2f}, Refund ID: {refund_id})"
    else:
        ans = f"Refund could not be completed: {exec_res.get('reason')}"
        action = "escalate"
        summary = f"Refund execution refused: {exec_res.get('reason')}"

    dur = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "answer": ans,
        "action": action,
        "tool_history": tool_entry,
        "trace": [{
            "node": "auto_execute",
            "summary": summary,
            "duration_ms": dur
        }]
    }


def hitl_interrupt_node(state: SupportState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    order_id = state.get("extracted_order_id")
    user_id = state.get("user_id", "user_1")
    session_id = state.get("session_id", "default_session")
    amount = state.get("amount_at_risk")
    lang = state.get("language", "en")

    if amount is None:
        order = get_order(order_id)
        amount = float(order.get("amount", 0.0)) if order else 0.0

    policy_res = state.get("policy_decision", {})

    # Build handoff dossier for supervisor review
    dossier = generate_handoff_dossier(
        state=state,
        issue_summary=f"High-value refund request for order {order_id} of Rs {amount:.2f} requires human supervisor approval",
        proposed_action=f"execute_refund for {order_id} of Rs {amount:.2f}",
        proposed_amount=amount,
        policy_decision=policy_res,
        tool_history=state.get("tool_history", [])
    )
    why_dec = {
        "intent": state.get("intent", "refund_request"),
        "confidence": round(float(state.get("intent_confidence", 0.0)), 2),
        "policy_rule": "High-Value Transaction Threshold (> Rs 2,000)",
        "final_route": "hitl_approval",
        "reason": f"Order {order_id} is eligible but refund amount (Rs {amount:.2f}) exceeds automated threshold (> Rs 2,000). Paused for supervisor review."
    }
    dossier["why_decision"] = why_dec

    # Pause execution awaiting human supervisor decision
    interrupt_payload = {
        "type": "human_approval_required",
        "message": f"Refund of Rs {amount:.2f} for order {order_id} requires supervisor approval.",
        "dossier": dossier,
        "why_decision": why_dec
    }
    resume_data = interrupt(interrupt_payload)

    # Resume from interrupt
    if isinstance(resume_data, dict):
        status = str(resume_data.get("status", "")).lower()
        supervisor = resume_data.get("supervisor", "sup_supervisor")
    else:
        status = "approved" if "approv" in str(resume_data).lower() else "rejected"
        supervisor = "sup_supervisor"

    if status == "approved":
        exec_res = execute_refund(
            order_id=order_id,
            amount=amount,
            reason="Customer refund approved by supervisor",
            approved_by=supervisor,
            user_id=user_id,
            session=session_id
        )
        refund_id = exec_res.get("refund_id", "REF-APPROVED")
        ans = (
            f"Aapka order {order_id} ka refund Rs {amount:.2f} supervisor {supervisor} dwara approve ho gaya hai aur successfully execute ho gaya hai. Refund ID: {refund_id}."
            if lang == "hinglish" else
            f"Your refund request for order {order_id} of Rs {amount:.2f} has been approved by supervisor {supervisor} and processed successfully. Refund ID: {refund_id}."
        )
        action = "answer"
        tool_entry = [{
            "tool": "execute_refund",
            "input": {"order_id": order_id, "amount": amount, "approved_by": supervisor},
            "result": exec_res
        }]
        summary = f"Supervisor {supervisor} approved refund for {order_id} (Rs {amount:.2f}). Executed."
    else:
        log_audit(
            session_id,
            "hitl_approval",
            {"order_id": order_id, "amount": amount, "supervisor": supervisor},
            "REJECTED_BY_SUPERVISOR",
            f"Refund declined by supervisor {supervisor}"
        )
        ans = (
            f"Aapka order {order_id} ka refund request supervisor {supervisor} dwara review karke decline kar diya gaya hai."
            if lang == "hinglish" else
            f"Your refund request for order {order_id} of Rs {amount:.2f} was reviewed by supervisor {supervisor} and declined under company policy."
        )
        action = "reject"
        tool_entry = [{
            "tool": "supervisor_review",
            "input": {"order_id": order_id, "amount": amount, "decision": "rejected"},
            "result": "declined"
        }]
        summary = f"Supervisor {supervisor} rejected refund for {order_id} (Rs {amount:.2f})"

    dur = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "answer": ans,
        "action": action,
        "handoff_dossier": dossier,
        "tool_history": tool_entry,
        "trace": [{
            "node": "hitl_interrupt",
            "summary": summary,
            "duration_ms": dur
        }]
    }


def build_why_decision(state: SupportState) -> Dict[str, Any]:
    """
    Constructs explainability metadata:
    {intent, confidence, policy_rule, final_route, reason}
    """
    intent = state.get("intent", "unknown")
    conf = round(float(state.get("intent_confidence", 0.0)), 2)
    action = state.get("action", "answer")
    force_escalate = state.get("force_escalate", False)
    grounded = state.get("grounded")
    policy = state.get("policy_decision")
    order_id = state.get("extracted_order_id")
    sentiment = state.get("sentiment", "neutral")
    priority = state.get("priority", "Low")

    trace_nodes = [t.get("node") for t in state.get("trace", [])]

    # 1. Security injection block
    if "injection" in trace_nodes and force_escalate and "triage" not in trace_nodes:
        return {
            "intent": "security_alert",
            "confidence": 1.0,
            "policy_rule": "Anti-Jailbreak & Prompt Injection Defense Policy",
            "final_route": "security_hold",
            "reason": "Input triggered prompt injection or jailbreak heuristics. Blocked and safe refusal returned."
        }

    # 2. Direct escalation due to hostile sentiment or critical priority
    if sentiment == "abusive":
        return {
            "intent": intent,
            "confidence": conf,
            "policy_rule": "Customer Safety & Sentiment Escalation Policy",
            "final_route": "human_handoff",
            "reason": "User query contained hostile or abusive language; escalated directly to human supervisor."
        }
    if priority == "Critical" and not order_id and not state.get("is_transactional"):
        return {
            "intent": intent,
            "confidence": conf,
            "policy_rule": "High-Priority Customer Escalation Policy",
            "final_route": "human_handoff",
            "reason": "Inquiry classified as Critical priority without order context; expedited to human specialist."
        }

    # 3. Transactional Policy Gate paths
    if state.get("is_transactional") or policy:
        if not order_id:
            return {
                "intent": intent,
                "confidence": conf,
                "policy_rule": "Order Identification Prerequisite",
                "final_route": "clarify",
                "reason": "Transactional request requires an Order ID (e.g. ORD-1001) to verify policy eligibility."
            }

        if policy:
            eligible = policy.get("eligible", False)
            requires_hitl = policy.get("requires_human_approval", False)
            p_reason = policy.get("reason", "")

            if not eligible:
                return {
                    "intent": intent,
                    "confidence": conf,
                    "policy_rule": "Refund Eligibility Gate (14-day window, ownership, refund status)",
                    "final_route": "reject",
                    "reason": f"Order {order_id} failed policy checks: {p_reason}"
                }
            elif requires_hitl:
                return {
                    "intent": intent,
                    "confidence": conf,
                    "policy_rule": "High-Value Transaction Threshold (> Rs 2,000)",
                    "final_route": "hitl_approval",
                    "reason": f"Order {order_id} is eligible but exceeds automated limit (> Rs 2,000). Paused for supervisor approval."
                }
            else:
                return {
                    "intent": intent,
                    "confidence": conf,
                    "policy_rule": "Automated Refund Execution Gate (<= Rs 2,000, delivered <= 14 days)",
                    "final_route": "auto_execute",
                    "reason": f"Order {order_id} verified delivered within 14 days and within automated limit. Refund processed."
                }

    # 4. RAG Grounding paths
    if grounded is True:
        cat = state.get("retrieved_docs", [{}])[0].get("category", intent) if state.get("retrieved_docs") else intent
        return {
            "intent": intent,
            "confidence": conf,
            "policy_rule": f"Knowledge Base Grounding Policy ({cat})",
            "final_route": "rag_answer",
            "reason": f"Retrieved relevant documentation from '{cat}' and factual claims were verified against source text."
        }
    elif grounded is False:
        return {
            "intent": intent,
            "confidence": conf,
            "policy_rule": "Hallucination Prevention & Factual Grounding Enforcement",
            "final_route": "human_handoff",
            "reason": "Generated answer failed 2-pass strict grounding check against knowledge base; escalated to human specialist."
        }
    elif action == "clarify":
        return {
            "intent": intent,
            "confidence": conf,
            "policy_rule": "Low Confidence Query Resolution Policy",
            "final_route": "clarify",
            "reason": f"Intent confidence ({conf:.2f}) fell below 0.60 threshold; requested clarification from customer."
        }

    # Default fallback
    return {
        "intent": intent,
        "confidence": conf,
        "policy_rule": "Standard Support Workflow Policy",
        "final_route": action,
        "reason": f"Request processed with action '{action}' under standard support guidelines."
    }


def rag_node(state: SupportState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    query = state.get("sanitized_query") or state.get("user_query", "")
    lang = state.get("language", "en")
    query_en = state.get("query_en") or normalize_to_english(query, lang)
    intent = state.get("intent", "unknown")
    intent_confidence = state.get("intent_confidence", 0.0)

    # If intent == "unknown" and confidence is low, route to clarify
    if intent == "unknown" and intent_confidence < 0.6:
        clarify_msg = (
            "Kripya apni query thoda aur detail me batayein taaki hum aapki behtar madad kar sakein."
            if lang == "hinglish" else
            "Could you please clarify your request so I can assist you better?"
        )
        dur = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "retrieved_docs": [],
            "answer": clarify_msg,
            "action": "clarify",
            "trace": [{
                "node": "rag",
                "summary": "Low confidence unknown query, requesting clarification",
                "duration_ms": dur
            }]
        }

    # Intent-filtered retrieval
    category_map = {
        "refund_request": "refunds",
        "refunds": "refunds",
        "billing_dispute": "billing",
        "billing": "billing",
        "login": "login",
        "subscription": "subscription"
    }
    retrieval_cat = category_map.get(intent)
    if not (retrieval_cat and intent_confidence >= 0.6):
        retrieval_cat = None

    # Retrieve with relevance scores and build structured citations
    results = retrieve_with_scores(query_en, category=retrieval_cat, k=4)
    docs = []
    citations = []
    seen_keys = set()
    for doc, score in results:
        cit = build_citation(doc, score)
        key = cit.get("source") or (cit.get("title"), cit.get("category"))
        if key not in seen_keys:
            seen_keys.add(key)
            citations.append(cit)
            docs.append(doc)

    context = "\n\n".join(d.page_content for d in docs)

    history = state.get("history", [])
    history_context = ""
    if history:
        recent = history[-4:]
        history_context = "\nRecent Conversation Turns:\n" + "\n".join(
            f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}" for m in recent
        )

    prompt = f"""Answer ONLY using the context below.
Do NOT add any information not explicitly stated.

Context:
{context}
{history_context}
Question:
{query}

Language Instruction:
User language style: {lang.upper()}
- If user query is in Hinglish (Roman Hindi), reply politely in natural conversational Hinglish.
- If user query is in Hindi, reply in Hindi.
- If user query is in English, reply in English.
Maintain a warm, polite customer support tone.
"""
    try:
        answer = LLM.invoke(prompt).content.strip()
    except Exception:
        answer = context.split("\n\n")[0].strip() if context else "Based on our documentation, here is what we found."

    dur = round((time.perf_counter() - t0) * 1000, 2)
    top_title = citations[0]["title"] if citations else "None"
    top_score = citations[0]["score"] if citations else 0.0

    return {
        "retrieved_docs": citations,
        "answer": answer,
        "context": context,
        "action": "answer",
        "trace": [{
            "node": "rag",
            "summary": f"Retrieved {len(citations)} citations (top: '{top_title}', score={top_score:.2f})",
            "duration_ms": dur
        }]
    }


def grounding_node(state: SupportState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    ans = state.get("answer", "")
    context = state.get("context", "")
    lang = state.get("language", "en")
    query = state.get("sanitized_query") or state.get("user_query", "")

    # 1. First-pass grounding check
    first_grounded = is_grounded(ans, context) if (context and ans) else False

    if first_grounded:
        dur = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "grounded": True,
            "action": "answer",
            "force_escalate": False,
            "trace": [{
                "node": "grounding",
                "summary": "Answer verified: fully grounded in knowledge base documentation",
                "duration_ms": dur
            }]
        }

    # 2. First check failed -> Regenerate ONCE with stricter prompt
    strict_prompt = f"""You are a strict, factual customer support verification assistant.
Your task is to answer the customer's question using ONLY the verbatim facts in the context below.

CRITICAL RULES:
1. Do NOT extrapolate, assume, speculate, or introduce any facts not explicitly stated in the context.
2. If the context does not contain enough verified information to answer the question directly and completely, respond EXACTLY with:
"I do not have enough verified information in our documentation to answer this question."

Context:
{context}

Question:
{query}

Language: {lang.upper()}
- If language is HINGLISH, reply politely in natural conversational Hinglish.
- If language is HINDI, reply in Hindi.
- If language is ENGLISH, reply in English.
Provide a concise, direct, strictly grounded answer:"""

    try:
        regenerated_ans = LLM.invoke(strict_prompt).content.strip()
    except Exception:
        regenerated_ans = "I do not have enough verified information in our documentation to answer this question."

    # 3. Check if regenerated answer is a refusal or still ungrounded
    is_refusal = (
        "not have enough verified information" in regenerated_ans.lower()
        or "unable to find" in regenerated_ans.lower()
        or "cannot answer" in regenerated_ans.lower()
        or len(regenerated_ans.strip()) < 10
    )

    second_grounded = False if is_refusal else (is_grounded(regenerated_ans, context) if context else False)
    dur = round((time.perf_counter() - t0) * 1000, 2)

    if second_grounded:
        return {
            "answer": regenerated_ans,
            "grounded": True,
            "action": "answer",
            "force_escalate": False,
            "trace": [{
                "node": "grounding",
                "summary": "Initial answer failed grounding; regenerated answer passed strict verification",
                "duration_ms": dur
            }]
        }

    # 4. Still false -> Route to handoff instead of answering
    dossier = generate_handoff_dossier(
        state=state,
        issue_summary="Inquiry could not be factually grounded in knowledge base documentation after strict regeneration",
        proposed_action="Route to human support specialist for unverified inquiry"
    )
    escalate_msg = (
        "Dokumentation ke anusaar hum is vishay par nishchit jankari uplabdh nahi kara sakte. Hum aapko human support specialist ko transfer kar rahe hain."
        if lang == "hinglish" else
        "I could not verify a reliable answer from our knowledge base for this inquiry. I have escalated your request to a human support specialist."
    )

    return {
        "answer": escalate_msg,
        "grounded": False,
        "action": "escalate",
        "force_escalate": True,
        "handoff_dossier": dossier,
        "trace": [{
            "node": "grounding",
            "summary": "Failed 2-pass strict grounding check; safely escalated to human specialist handoff",
            "duration_ms": dur
        }]
    }


def respond_node(state: SupportState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    user_q = state.get("user_query", "")
    ans = state.get("answer", "")
    action = state.get("action", "answer")
    citations = state.get("retrieved_docs", [])
    grounded = state.get("grounded")
    why_dec = state.get("why_decision") or build_why_decision(state)

    turn_events = [
        {"role": "user", "content": user_q},
        {
            "role": "assistant",
            "content": ans,
            "action": action,
            "citations": citations,
            "grounded": grounded,
            "why_decision": why_dec
        }
    ]
    dur = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "why_decision": why_dec,
        "history": turn_events,
        "messages": turn_events,
        "trace": [{
            "node": "respond",
            "summary": f"Completed response turn (route='{why_dec['final_route']}', action='{action}')",
            "duration_ms": dur
        }]
    }


# ============================================================================
# 2. Conditional Routing Logic
# ============================================================================

def route_from_triage(s: SupportState) -> str:
    """
    Routing rules from triage:
    - abusive sentiment -> escalate
    - critical priority without order ID -> escalate (direct human handoff)
    - transactional (is_transactional=True) -> policy_gate
    - faq / informational / unknown -> rag
    """
    if s.get("sentiment") == "abusive":
        return "escalate"
    if s.get("priority") == "Critical" and not s.get("extracted_order_id"):
        return "escalate"
    if s.get("is_transactional"):
        return "policy_gate"
    return "rag"


def route_from_policy_gate(s: SupportState) -> str:
    """
    Policy Gate branches:
    - Missing order ID -> respond (clarify asked)
    - Not eligible -> reject
    - Eligible and requires_human_approval -> hitl_interrupt
    - Eligible and auto -> auto_execute
    """
    if not s.get("extracted_order_id"):
        return "respond"

    decision = s.get("policy_decision", {})
    if not decision.get("eligible"):
        return "reject"
    if decision.get("requires_human_approval"):
        return "hitl_interrupt"
    return "auto_execute"


# ============================================================================
# 3. Graph Builder & Checkpointer Compilation
# ============================================================================

def build_graph(checkpointer: Optional[Any] = None):
    """
    Compiles the target customer support multi-agent graph with LangGraph MemorySaver:
    pii -> injection -> triage -> {rag -> grounding} OR {policy_gate -> (reject | auto_execute | hitl_interrupt)} -> respond
    """
    builder = StateGraph(SupportState)

    builder.add_node("pii", pii_node)
    builder.add_node("injection", injection_node)
    builder.add_node("triage", triage_node)
    builder.add_node("escalate", escalate_node)

    builder.add_node("policy_gate", policy_gate_node)
    builder.add_node("reject", reject_node)
    builder.add_node("auto_execute", auto_execute_node)
    builder.add_node("hitl_interrupt", hitl_interrupt_node)

    builder.add_node("rag", rag_node)
    builder.add_node("grounding", grounding_node)

    builder.add_node("respond", respond_node)

    # 1. Pipeline entry
    builder.add_edge(START, "pii")
    builder.add_edge("pii", "injection")

    # 2. Injection branch: security block routes directly to respond, else triage
    builder.add_conditional_edges(
        "injection",
        lambda s: "respond" if s.get("force_escalate") else "triage",
        {
            "respond": "respond",
            "triage": "triage"
        }
    )

    # 3. Triage branch: abusive -> escalate, transactional -> policy_gate, faq -> rag
    builder.add_conditional_edges(
        "triage",
        route_from_triage,
        {
            "escalate": "escalate",
            "policy_gate": "policy_gate",
            "rag": "rag"
        }
    )

    builder.add_edge("escalate", "respond")

    # 4. Policy Gate branch: reject | auto_execute | hitl_interrupt | respond (clarify)
    builder.add_conditional_edges(
        "policy_gate",
        route_from_policy_gate,
        {
            "respond": "respond",
            "reject": "reject",
            "auto_execute": "auto_execute",
            "hitl_interrupt": "hitl_interrupt"
        }
    )

    builder.add_edge("reject", "respond")
    builder.add_edge("auto_execute", "respond")
    builder.add_edge("hitl_interrupt", "respond")

    # 5. RAG branch: clarify -> respond, else grounding -> respond
    builder.add_conditional_edges(
        "rag",
        lambda s: "respond" if s.get("action") == "clarify" else "grounding",
        {
            "respond": "respond",
            "grounding": "grounding"
        }
    )

    builder.add_edge("grounding", "respond")

    # 6. Response ends execution
    builder.add_edge("respond", END)

    # Compile with MemorySaver checkpointer
    chk = checkpointer if checkpointer is not None else MemorySaver()
    compiled = builder.compile(checkpointer=chk)

    # Monkey-patch invoke to defensively supply thread_id when invoked without config
    orig_invoke = compiled.invoke
    def safe_invoke(input_data, config=None, **kwargs):
        if config is None:
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        elif isinstance(config, dict) and "configurable" not in config:
            config = {"configurable": config}
        elif isinstance(config, dict) and "thread_id" not in config.get("configurable", {}):
            config["configurable"]["thread_id"] = str(uuid.uuid4())
        return orig_invoke(input_data, config=config, **kwargs)

    compiled.invoke = safe_invoke
    return compiled