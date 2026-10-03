from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import streamlit as st

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")


model = "openai/gpt-oss-20b"
run_name = "CustomerSupportLangGraph"

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    try:
        groq_api_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        pass


_primary = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=groq_api_key or "gsk_placeholder",
    temperature=0.2
)
_fallbacks = [
    ChatGroq(model="qwen/qwen3.8-27b", api_key=groq_api_key or "gsk_placeholder", temperature=0.2),
    ChatGroq(model="openai/gpt-oss-20b", api_key=groq_api_key or "gsk_placeholder", temperature=0.2),
]
LLM = _primary.with_fallbacks(_fallbacks)

# Policy & Action Layer Thresholds
REFUND_WINDOW_DAYS = 14
REFUND_AUTO_APPROVE_LIMIT = 2000.0
MOCK_DB_PATH = os.path.join(BASE_DIR, "data", "mock_support.db")






