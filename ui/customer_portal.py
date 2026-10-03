import os
import time
import uuid
import streamlit as st

from ui.shared import (
    DEMO_USERS,
    get_graph,
    get_current_thread_messages,
    add_message,
    record_pii_detections,
    get_badge_html
)
from utils.mock_db import get_user


def render_message_item(msg):
    role = msg.get("role", "user")
    with st.chat_message(role):
        if msg.get("pending_approval"):
            st.warning(
                f"⏳ **Supervisor Approval Required**\n\n"
                f"{msg.get('content', 'Your request is currently awaiting human supervisor review in the Command Center.')}"
            )
        else:
            # Grounding Badge for Assistant Responses
            if role == "assistant":
                grounded = msg.get("grounded")
                action = msg.get("action")
                if grounded is True:
                    st.markdown(
                        '<div style="display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:12px; '
                        'background:rgba(40,167,69,0.12); color:#28a745; font-size:12px; font-weight:600; margin-bottom:8px;">'
                        '<span>🛡️ Grounded</span>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                elif grounded is False:
                    st.markdown(
                        '<div style="display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:12px; '
                        'background:rgba(220,53,69,0.12); color:#dc3545; font-size:12px; font-weight:600; margin-bottom:8px;">'
                        '<span>⚠️ Not verified</span>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                elif action in ["auto_execute", "reject"]:
                    st.markdown(
                        '<div style="display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:12px; '
                        'background:rgba(23,162,184,0.12); color:#17a2b8; font-size:12px; font-weight:600; margin-bottom:8px;">'
                        '<span>⚖️ Policy Verified</span>'
                        '</div>',
                        unsafe_allow_html=True
                    )

            st.markdown(msg.get("content", ""))

        if role == "assistant":
            # 1. Expandable Evidence Cards
            docs = msg.get("retrieved_docs") or msg.get("citations") or []
            if docs:
                with st.expander(f"📚 Retrieved Evidence & Citations ({len(docs)})", expanded=False):
                    for idx, doc in enumerate(docs, 1):
                        if isinstance(doc, dict):
                            title = doc.get("title", f"Document {idx}")
                            cat = str(doc.get("category", "General")).title()
                            score = doc.get("score", 0.0)
                            snippet = doc.get("snippet", "")
                            src = doc.get("source", "")
                            filename = os.path.basename(src) if src else "Knowledge Base Document"

                            st.markdown(
                                f"""
<div style="border: 1px solid rgba(128,128,128,0.2); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; background: rgba(128,128,128,0.03);">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <span style="font-weight: 600; font-size: 14px;">📄 {title}</span>
        <span style="font-size: 11px; padding: 2px 8px; border-radius: 10px; background: #e9ecef; color: #495057;">{cat}</span>
    </div>
    <div style="font-size: 12px; color: #6c757d; margin-bottom: 6px;">
        Relevance Score: <code>{score:.2f}</code> | <em>{filename}</em>
    </div>
    <div style="font-size: 13px; font-style: italic; border-left: 3px solid #007bff; padding-left: 8px; margin-top: 4px; color: #333;">
        "{snippet}"
    </div>
</div>
""",
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(f"- 📄 `{str(doc)}`")

            # 2. "Why this decision?" Panel
            why_decision = msg.get("why_decision")
            if why_decision and isinstance(why_decision, dict):
                with st.expander("💡 Why this decision?", expanded=False):
                    intent_val = why_decision.get("intent", "N/A")
                    conf_val = why_decision.get("confidence", 0.0)
                    policy_rule = why_decision.get("policy_rule", "N/A")
                    final_route = why_decision.get("final_route", "N/A")
                    reason_val = why_decision.get("reason", "N/A")

                    st.markdown(
                        f"""
- **Intent**: `{intent_val}` (Confidence: `{conf_val:.2f}` / `{int(conf_val * 100)}%`)
- **Policy Rule Applied**: {policy_rule}
- **Final Route**: `{final_route}`
- **Reason**: {reason_val}
"""
                    )

            # 3. Trace Timeline Expander
            trace = msg.get("trace", [])
            if trace:
                with st.expander("🔍 Agent steps (Trace Timeline)", expanded=False):
                    timeline_rows = []
                    total_dur = 0.0
                    for step_idx, step in enumerate(trace, 1):
                        dur = step.get("duration_ms", 0.0)
                        total_dur += dur
                        node = step.get("node", "step").upper()
                        summary = step.get("summary", "")
                        timeline_rows.append(f"| **{step_idx}. {node}** | {summary} | `{dur:.1f} ms` |")

                    header = "| Step | Agent / Node Execution | Duration |\n|---|---|---|\n"
                    footer = f"\n\n*Total Execution Time: `{total_dur:.1f} ms`*"
                    st.markdown(header + "\n".join(timeline_rows) + footer)


def render_customer_portal():
    st.markdown("### 💬 Customer Portal")

    # 1. Top Controls: User Selector and Active Thread Bar
    col_user, col_thread, col_new = st.columns([4, 4, 2])

    with col_user:
        current_uid = st.session_state.get("current_user_id", "user_1")
        user_index = next((i for i, u in enumerate(DEMO_USERS) if u["user_id"] == current_uid), 0)
        selected_user = st.selectbox(
            "Logged In As:",
            options=DEMO_USERS,
            index=user_index,
            format_func=lambda u: f"{u['name']} ({u['user_id']}) - {'✓ Verified' if u['verified'] else '⚠ Unverified'}",
            key="customer_user_selector"
        )
        if selected_user["user_id"] != current_uid:
            st.session_state.current_user_id = selected_user["user_id"]

    with col_new:
        st.write("")  # spacing
        st.write("")
        if st.button("➕ New Chat", key="btn_new_chat", width="stretch", help="Start a new support conversation"):
            new_tid = f"thread_{uuid.uuid4().hex[:6]}"
            st.session_state.thread_id = new_tid
            st.session_state.messages_by_thread[new_tid] = []

    with col_thread:
        current_tid = st.session_state.get("thread_id", "thread_001")
        st.text_input("Active Thread ID", value=current_tid, disabled=True, key="active_thread_display")

    # 2. Dynamic Badges Bar (reflecting latest turn's classification)
    tracked = st.session_state.get("tracked_threads", {}).get(st.session_state.thread_id, {})
    latest_lang = tracked.get("language", "English").capitalize()
    latest_priority = tracked.get("priority", "Low")
    latest_sentiment = tracked.get("sentiment", "Neutral").capitalize()

    p_colors = {"Low": "#28a745", "Medium": "#17a2b8", "High": "#fd7e14", "Critical": "#dc3545"}
    s_colors = {"Positive": "#28a745", "Neutral": "#6c757d", "Frustrated": "#fd7e14", "Abusive": "#dc3545"}

    badge_html = f"""
    <div style="display: flex; flex-wrap: wrap; margin-bottom: 15px; padding: 8px 12px; background: rgba(0,0,0,0.03); border-radius: 8px;">
        {get_badge_html('Language', latest_lang, '#4A90E2')}
        {get_badge_html('Priority', latest_priority, p_colors.get(latest_priority, '#6c757d'))}
        {get_badge_html('Sentiment', latest_sentiment, s_colors.get(latest_sentiment, '#6c757d'))}
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)

    # 3. Message History
    messages = get_current_thread_messages()
    if not messages:
        st.info("👋 Hello! How can we assist you with your orders, refunds, or general queries today?")

    for msg in messages:
        render_message_item(msg)

    # 4. Chat Input & Invocation Handling
    user_input = st.chat_input("Ask a question, enter an order ID, or request a refund...")
    if user_input and user_input.strip():
        # Check if current thread is already paused awaiting approval
        if tracked.get("interrupted"):
            st.error("⚠️ This conversation is currently paused waiting for supervisor approval. Please await review in the Command Center.")
            return

        # Add user turn to session state and render immediately
        add_message("user", user_input.strip())
        with st.chat_message("user"):
            st.markdown(user_input.strip())

        try:
            graph = get_graph()
            cfg = {"configurable": {"thread_id": st.session_state.thread_id}}
            inputs = {
                "user_query": user_input.strip(),
                "user_id": st.session_state.current_user_id,
                "session_id": st.session_state.thread_id
            }

            res = graph.invoke(inputs, config=cfg)
            
            # Check for LangGraph HITL Interrupt
            is_interrupted = bool(res.get("__interrupt__"))
            
            # Extract state values from res
            lang = res.get("language", "en")
            priority = res.get("priority", "Low")
            sentiment = res.get("sentiment", "neutral")
            sla_deadline = res.get("sla_deadline")
            trace = res.get("trace", [])
            pii_counts = res.get("pii_counts", {})
            redacted_pii = res.get("redacted_pii", {})

            # Record any detected PII to live feed
            record_pii_detections(st.session_state.thread_id, st.session_state.current_user_id, redacted_pii)

            user_rec = get_user(st.session_state.current_user_id) or {}
            user_name = user_rec.get("name", st.session_state.current_user_id)

            if is_interrupted:
                interrupt_data = res["__interrupt__"][0].value
                dossier = interrupt_data.get("dossier", {})
                friendly_wait_msg = (
                    f"Your refund request for order {res.get('extracted_order_id', 'specified')} "
                    f"(Rs {dossier.get('amount', 0):,.2f}) exceeds automated threshold and requires supervisor approval. "
                    f"Our team has received the dossier and is reviewing it now."
                )

                # Update tracked thread metadata
                st.session_state.tracked_threads[st.session_state.thread_id] = {
                    "thread_id": st.session_state.thread_id,
                    "user_id": st.session_state.current_user_id,
                    "user_name": user_name,
                    "status": "pending_approval",
                    "priority": priority,
                    "sentiment": sentiment,
                    "language": lang,
                    "sla_deadline": sla_deadline,
                    "interrupted": True,
                    "dossier": dossier,
                    "pii_counts": pii_counts,
                    "last_query": user_input.strip(),
                    "last_answer": friendly_wait_msg,
                    "trace": trace,
                    "action": "hitl_interrupt"
                }

                # Add assistant pending approval message & render
                add_message(
                    "assistant",
                    friendly_wait_msg,
                    pending_approval=True,
                    trace=trace,
                    dossier=dossier,
                    why_decision=dossier.get("why_decision"),
                    action="hitl_interrupt"
                )
                with st.chat_message("assistant"):
                    st.warning(f"⏳ **Supervisor Approval Required**\n\n{friendly_wait_msg}")
            else:
                action = res.get("action", "answer")
                answer = res.get("answer", "Response generated.")
                grounded = res.get("grounded")
                retrieved_docs = res.get("retrieved_docs", [])
                why_decision = res.get("why_decision")

                thread_status = (
                    "auto_resolved" if action == "answer" and not res.get("force_escalate")
                    else ("escalated" if action == "escalate" or res.get("force_escalate")
                    else "rejected" if action == "reject"
                    else "active")
                )

                st.session_state.tracked_threads[st.session_state.thread_id] = {
                    "thread_id": st.session_state.thread_id,
                    "user_id": st.session_state.current_user_id,
                    "user_name": user_name,
                    "status": thread_status,
                    "priority": priority,
                    "sentiment": sentiment,
                    "language": lang,
                    "sla_deadline": sla_deadline,
                    "interrupted": False,
                    "dossier": res.get("handoff_dossier"),
                    "pii_counts": pii_counts,
                    "last_query": user_input.strip(),
                    "last_answer": answer,
                    "trace": trace,
                    "action": action,
                    "grounded": grounded,
                    "retrieved_docs": retrieved_docs,
                    "why_decision": why_decision
                }

                add_message(
                    "assistant",
                    answer,
                    trace=trace,
                    grounded=grounded,
                    retrieved_docs=retrieved_docs,
                    why_decision=why_decision,
                    action=action
                )
                assistant_msg = {
                    "role": "assistant",
                    "content": answer,
                    "trace": trace,
                    "grounded": grounded,
                    "retrieved_docs": retrieved_docs,
                    "why_decision": why_decision,
                    "action": action
                }
                render_message_item(assistant_msg)

        except Exception as e:
            friendly_error = "We experienced a temporary system error processing your request. Please try again."
            add_message("assistant", friendly_error)
            with st.chat_message("assistant"):
                st.markdown(friendly_error)
            st.error(f"Support System Notice: {friendly_error}")
