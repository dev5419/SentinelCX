import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import streamlit as st

from core.graph import build_graph
from utils.mock_db import get_user, reset_db, get_audit_logs


DEMO_USERS = [
    {"user_id": "user_1", "name": "Alice Johnson", "email": "alice@example.com", "verified": True},
    {"user_id": "user_2", "name": "Bob Smith", "email": "bob@example.com", "verified": True},
    {"user_id": "user_3", "name": "Charlie Davis", "email": "charlie@example.com", "verified": False},
    {"user_id": "user_4", "name": "Diana Prince", "email": "diana@example.com", "verified": True},
    {"user_id": "user_5", "name": "Evan Wright", "email": "evan@example.com", "verified": True},
    {"user_id": "user_6", "name": "Fiona Gallagher", "email": "fiona@example.com", "verified": False},
]


@st.cache_resource
def get_graph():
    """Returns singleton compiled LangGraph with MemorySaver checkpointer."""
    return build_graph()


def init_session_state():
    """Ensures all session state variables exist with safe defaults."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"thread_{uuid.uuid4().hex[:6]}"
    if "current_user_id" not in st.session_state:
        st.session_state.current_user_id = "user_1"
    if "messages_by_thread" not in st.session_state:
        st.session_state.messages_by_thread = {}
    if "tracked_threads" not in st.session_state:
        st.session_state.tracked_threads = {}
    if "pii_feed" not in st.session_state:
        st.session_state.pii_feed = []


def reset_demo():
    """Reseeds the database and resets session states."""
    reset_db()
    new_thread = f"thread_{uuid.uuid4().hex[:6]}"
    st.session_state.thread_id = new_thread
    st.session_state.current_user_id = "user_1"
    st.session_state.messages_by_thread = {new_thread: []}
    st.session_state.tracked_threads = {}
    st.session_state.pii_feed = []


def get_current_thread_messages() -> List[Dict[str, Any]]:
    tid = st.session_state.get("thread_id", "default_thread")
    if "messages_by_thread" not in st.session_state:
        st.session_state.messages_by_thread = {}
    if tid not in st.session_state.messages_by_thread:
        st.session_state.messages_by_thread[tid] = []
    return st.session_state.messages_by_thread[tid]


def add_message(role: str, content: str, **kwargs):
    tid = st.session_state.get("thread_id", "default_thread")
    msgs = get_current_thread_messages()
    msg = {"role": role, "content": content, "timestamp": datetime.now(timezone.utc).isoformat()}
    msg.update(kwargs)
    msgs.append(msg)


def record_pii_detections(thread_id: str, user_id: str, redacted_pii: Dict[str, str]):
    """Records live PII redactions to the supervisor feed."""
    if not redacted_pii:
        return
    now_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    for token, raw_val in redacted_pii.items():
        clean_type = "OTHER"
        for ptype in ["EMAIL", "PHONE", "AADHAAR", "CARD", "OTP"]:
            if ptype in token.upper():
                clean_type = ptype
                break
        st.session_state.pii_feed.insert(0, {
            "timestamp": now_str,
            "thread_id": thread_id,
            "user_id": user_id,
            "type": clean_type,
            "masked_value": token
        })


def get_sla_status(sla_deadline_str: Optional[str]) -> Dict[str, Any]:
    """Calculates remaining time until SLA deadline and returns badge color and label."""
    if not sla_deadline_str:
        return {"label": "N/A", "color": "#6c757d", "expired": False, "remaining_seconds": 999999}
    try:
        deadline = datetime.fromisoformat(sla_deadline_str)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = (deadline - now).total_seconds()

        if diff <= 0:
            return {"label": "SLA BREACHED", "color": "#dc3545", "expired": True, "remaining_seconds": diff}

        mins = int(diff // 60)
        secs = int(diff % 60)
        hours = int(mins // 60)
        mins = mins % 60

        if hours > 0:
            time_str = f"{hours}h {mins}m remaining"
        else:
            time_str = f"{mins}m {secs}s remaining"

        color = "#28a745" if diff > 1800 else "#ffc107"  # green if > 30m, yellow if < 30m
        return {"label": time_str, "color": color, "expired": False, "remaining_seconds": diff}
    except Exception:
        return {"label": "Valid", "color": "#6c757d", "expired": False, "remaining_seconds": 999999}


def get_badge_html(label: str, value: str, color: str = "#4A90E2") -> str:
    """Renders a modern UI badge tag."""
    return f"""<span style="
        display: inline-block;
        padding: 3px 10px;
        margin-right: 6px;
        margin-bottom: 4px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        background-color: {color}22;
        color: {color};
        border: 1px solid {color}55;
    "><strong>{label}:</strong> {value}</span>"""
