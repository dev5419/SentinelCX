import streamlit as st

from ui import (
    init_session_state,
    reset_demo,
    render_customer_portal,
    render_supervisor_center
)


st.set_page_config(
    page_title="SentinelCX — Enterprise AI Customer Support & Supervision",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern, clean UI styling
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
    }
    .badge-card {
        padding: 10px 14px;
        border-radius: 8px;
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state tracking
init_session_state()

# =============================================================================
# Sidebar Controls & System Status
# =============================================================================
with st.sidebar:
    st.markdown("## ⚙️ Demo Controls")
    
    if st.button("🔄 Reset Demo", type="secondary", width="stretch", help="Reseeds the SQLite database and clears all conversation threads"):
        reset_demo()
        st.toast("Database re-seeded and session threads cleared!", icon="🧹")
        st.rerun()

    st.markdown("---")
    st.markdown("### 👥 Quick Reference Scenarios")
    st.caption("""
    - **Hinglish Refund (Auto):**
      - User: `user_1`
      - Query: `Mera order ORD-1001 ka refund chahiye please`
      - *Result:* Auto-executes (Rs 1,499 <= 2000 limit)
    
    - **High-Value Refund (HITL):**
      - User: `user_1`
      - Query: `Refund ORD-1005 for Rs 15000`
      - *Result:* Pauses at interrupt, appears in Tab 2 queue
    
    - **Abusive Message (Escalate):**
      - User: Any
      - Query: `You stupid useless bot refund my money right now`
      - *Result:* Routes to human support handoff with dossier
    
    - **Expired Window (Reject):**
      - User: `user_1`
      - Query: `Refund ORD-1002 please`
      - *Result:* Rejected (>14 days delivery) with policy quote
    """)

    st.markdown("---")
    st.markdown("### 🛡️ Enterprise Guardrails")
    st.markdown("""
    - 🔒 **PII Guard:** Regex masking for Phone, Email, Aadhaar, Cards, OTP
    - 🛑 **Injection Guard:** Jailbreak & roleplay detection with safe fallback
    - 🎯 **Triage Agent:** Intent, Sentiment, Priority & SLA computation
    - ⚖️ **Policy Gate:** Pure Python rule engine with deterministic limits
    - ⏸️ **LangGraph HITL:** State checkpointing with supervisor resume
    - 🔍 **Grounding Guard:** Context faithfulness verification
    """)


# =============================================================================
# Main Application Tabs
# =============================================================================
st.markdown("## 🤖 Autonomous Customer Support Multi-Agent System")

tab_customer, tab_supervisor = st.tabs([
    "💬 Customer Portal",
    "🛡️ Supervisor Command Center"
])

try:
    with tab_customer:
        render_customer_portal()

    with tab_supervisor:
        render_supervisor_center()
except Exception as e:
    st.error("A system error occurred. Please reset the demo or try again.")