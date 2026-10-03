import json
import streamlit as st
import pandas as pd
from langgraph.types import Command

from ui.shared import (
    get_graph,
    get_sla_status,
    get_badge_html
)
from utils.mock_db import get_audit_logs


@st.fragment
def render_supervisor_center():
    st.markdown("### 🛡️ Supervisor Command Center")

    # Header with auto-refresh notice & manual trigger
    col_hdr, col_btn = st.columns([8, 2])
    with col_hdr:
        st.caption("Live Supervisor Dashboard • Auto-refreshes every 5 seconds")
    with col_btn:
        if st.button("🔄 Refresh Data", width="stretch", key="sup_refresh_btn"):
            st.rerun()

    tracked_threads = st.session_state.get("tracked_threads", {})
    pii_feed = st.session_state.get("pii_feed", [])
    all_audit_logs = get_audit_logs(limit=150)

    # =========================================================================
    # 1. High-Level Metrics Row
    # =========================================================================
    total_active = sum(1 for t in tracked_threads.values() if t.get("status") in ["active", "pending_approval", "escalated"])
    auto_resolved_count = sum(1 for t in tracked_threads.values() if t.get("status") in ["auto_resolved", "approved"])
    escalated_count = sum(1 for t in tracked_threads.values() if t.get("status") == "escalated")
    pending_approval_count = sum(1 for t in tracked_threads.values() if t.get("interrupted") or t.get("status") == "pending_approval")

    # PII type counts from live feed
    pii_type_counts = {"PHONE": 0, "EMAIL": 0, "AADHAAR": 0, "CARD": 0, "OTP": 0}
    for item in pii_feed:
        ptype = item.get("type", "").upper()
        if ptype in pii_type_counts:
            pii_type_counts[ptype] += 1
        else:
            pii_type_counts[ptype] = 1

    total_pii_redactions = sum(pii_type_counts.values())

    # Priority counts
    prio_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for t in tracked_threads.values():
        p = t.get("priority", "Low")
        prio_counts[p] = prio_counts.get(p, 0) + 1

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            label="Active Tickets",
            value=total_active,
            delta=f"{pending_approval_count} pending approval" if pending_approval_count > 0 else None,
            delta_color="inverse"
        )
    with m2:
        st.metric(
            label="PII Redactions",
            value=total_pii_redactions,
            help=f"Phone: {pii_type_counts.get('PHONE', 0)}, Email: {pii_type_counts.get('EMAIL', 0)}, Card: {pii_type_counts.get('CARD', 0)}, Aadhaar: {pii_type_counts.get('AADHAAR', 0)}, OTP: {pii_type_counts.get('OTP', 0)}"
        )
    with m3:
        st.metric(
            label="Priority (Crit / High)",
            value=f"{prio_counts['Critical']} / {prio_counts['High']}",
            help=f"Critical: {prio_counts['Critical']}, High: {prio_counts['High']}, Medium: {prio_counts['Medium']}, Low: {prio_counts['Low']}"
        )
    with m4:
        st.metric(
            label="Auto-Resolved vs Escalated",
            value=f"{auto_resolved_count} / {escalated_count}",
            help="Auto-executed or answered without human vs escalated to specialist"
        )

    st.markdown("---")

    # =========================================================================
    # 2. Approval Queue (Interrupted Threads)
    # =========================================================================
    st.subheader(f"📋 Human-In-The-Loop Approval Queue ({pending_approval_count})")

    pending_threads = [
        t for t in tracked_threads.values()
        if t.get("interrupted") or t.get("status") == "pending_approval"
    ]

    if not pending_threads:
        st.success("✅ **Approval Queue is clear.** No tickets currently require supervisor review.")
    else:
        for ticket in pending_threads:
            tid = ticket.get("thread_id")
            user_id = ticket.get("user_id")
            user_name = ticket.get("user_name", user_id)
            dossier = ticket.get("dossier") or {}
            amount = dossier.get("amount", 0.0)
            policy_dec = dossier.get("policy_decision") or {}
            sla_info = get_sla_status(ticket.get("sla_deadline"))

            with st.container(border=True):
                c_title, c_sla = st.columns([7, 3])
                with c_title:
                    st.markdown(f"#### ⚠️ Ticket: `{tid}` — Refund of Rs {amount:,.2f}")
                    st.caption(f"Customer: **{user_name}** (`{user_id}`) | Priority: **{ticket.get('priority')}**")
                with c_sla:
                    st.markdown(
                        f"<div style='text-align: right;'>"
                        f"{get_badge_html('SLA', sla_info['label'], sla_info['color'])}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                # Dossier Details in 2 columns
                d1, d2 = st.columns(2)
                with d1:
                    st.markdown("**Issue Summary:**")
                    st.write(dossier.get("issue_summary", "High-value refund request"))
                    st.markdown("**Policy Gate Reason:**")
                    st.info(policy_dec.get("reason", "Requires human supervisor approval."))
                    if policy_dec.get("policy_quote"):
                        st.caption(f"📜 *Quote:* \"{policy_dec.get('policy_quote')}\"")

                with d2:
                    st.markdown("**Customer Details:**")
                    cust = dossier.get("customer_details", {})
                    st.write(f"- User ID: `{cust.get('user_id', user_id)}`")
                    st.write(f"- Original Query: *\"{cust.get('sanitized_query', ticket.get('last_query'))}\"*")
                    st.markdown("**Proposed Action:**")
                    st.code(dossier.get("proposed_action", f"execute_refund Rs {amount:.2f}"), language="text")

                # Action Controls
                st.markdown("---")
                btn_col1, btn_col2, sup_col = st.columns([3, 3, 4])

                with sup_col:
                    supervisor_id = st.text_input(
                        "Supervisor ID",
                        value="sup_lead_01",
                        key=f"sup_id_input_{tid}"
                    )

                with btn_col1:
                    if st.button("✅ Approve Refund", key=f"btn_approve_{tid}", type="primary", width="stretch"):
                        try:
                            graph = get_graph()
                            cfg = {"configurable": {"thread_id": tid}}
                            res = graph.invoke(
                                Command(resume={"status": "approved", "supervisor": supervisor_id.strip()}),
                                config=cfg
                            )
                            # Update thread info
                            ticket["status"] = "approved"
                            ticket["interrupted"] = False
                            ticket["last_answer"] = res.get("answer")
                            if "trace" in res:
                                ticket["trace"] = (ticket.get("trace") or []) + res["trace"]

                            # Sync messages for Customer Portal view
                            msgs = st.session_state.messages_by_thread.get(tid, [])
                            found = False
                            for m in msgs:
                                if m.get("pending_approval"):
                                    m["pending_approval"] = False
                                    m["content"] = res.get("answer")
                                    if "trace" in res:
                                        m["trace"] = (m.get("trace") or []) + res["trace"]
                                    found = True
                                    break
                            if not found:
                                msgs.append({
                                    "role": "assistant",
                                    "content": res.get("answer"),
                                    "trace": res.get("trace", [])
                                })

                            st.success(f"✓ Approved refund for ticket `{tid}`! Refund executed by `{supervisor_id}`.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error approving refund: {e}")

                with btn_col2:
                    if st.button("❌ Reject Request", key=f"btn_reject_{tid}", width="stretch"):
                        try:
                            graph = get_graph()
                            cfg = {"configurable": {"thread_id": tid}}
                            res = graph.invoke(
                                Command(resume={"status": "rejected", "supervisor": supervisor_id.strip()}),
                                config=cfg
                            )
                            ticket["status"] = "rejected"
                            ticket["interrupted"] = False
                            ticket["last_answer"] = res.get("answer")

                            msgs = st.session_state.messages_by_thread.get(tid, [])
                            for m in msgs:
                                if m.get("pending_approval"):
                                    m["pending_approval"] = False
                                    m["content"] = res.get("answer")
                                    break
                            else:
                                msgs.append({"role": "assistant", "content": res.get("answer")})

                            st.warning(f"Ticket `{tid}` refund rejected by `{supervisor_id}`.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error rejecting request: {e}")

    st.markdown("---")

    # =========================================================================
    # 3. Two Columns: Live PII Redaction Feed & SLA Countdown per Ticket
    # =========================================================================
    c_pii, c_sla = st.columns([5, 5])

    with c_pii:
        st.subheader("🔒 Live PII Redaction Feed")
        if not pii_feed:
            st.info("No PII detections recorded in this session.")
        else:
            pii_rows = []
            for item in pii_feed[:10]:
                pii_rows.append({
                    "Time": item.get("timestamp"),
                    "Thread": item.get("thread_id"),
                    "User": item.get("user_id"),
                    "Type": item.get("type"),
                    "Redaction": item.get("masked_value")
                })
            st.dataframe(pd.DataFrame(pii_rows), hide_index=True)

    with c_sla:
        st.subheader("⏱️ SLA Countdown per Ticket")
        if not tracked_threads:
            st.info("No tickets active in current session.")
        else:
            sla_rows = []
            for tid, t in tracked_threads.items():
                sla_stat = get_sla_status(t.get("sla_deadline"))
                sla_rows.append({
                    "Ticket": tid,
                    "User": t.get("user_name", t.get("user_id")),
                    "Priority": t.get("priority", "Low"),
                    "Status": t.get("status", "active"),
                    "SLA": sla_stat["label"]
                })
            st.dataframe(pd.DataFrame(sla_rows), hide_index=True)

    st.markdown("---")

    # =========================================================================
    # 4. Audit Log Viewer
    # =========================================================================
    st.subheader(f"📜 Audit Log Viewer ({len(all_audit_logs)} Entries)")

    f_col1, f_col2 = st.columns([4, 6])
    with f_col1:
        actions_list = ["ALL"] + sorted(list(set(log["action"] for log in all_audit_logs)))
        selected_action = st.selectbox("Filter by Action:", actions_list, key="audit_filter_action")
    with f_col2:
        search_query = st.text_input("Search Logs (Input / Reason / Decision):", key="audit_search_query")

    filtered_logs = all_audit_logs
    if selected_action != "ALL":
        filtered_logs = [l for l in filtered_logs if l["action"] == selected_action]
    if search_query and search_query.strip():
        q = search_query.lower().strip()
        filtered_logs = [
            l for l in filtered_logs
            if q in l["input"].lower() or q in l["reason"].lower() or q in l["decision"].lower() or q in l["session"].lower()
        ]

    if filtered_logs:
        df_logs = pd.DataFrame(filtered_logs)
        cols_to_show = ["log_id", "timestamp", "session", "action", "decision", "reason", "input"]
        df_logs = df_logs[[c for c in cols_to_show if c in df_logs.columns]]
        st.dataframe(df_logs, hide_index=True)
    else:
        st.caption("No audit log records match the selected filter.")
