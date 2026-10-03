import os
import glob
from functools import lru_cache
from typing import Dict, Any, List, Tuple
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from config import CHROMA_DIR, BASE_DIR

@lru_cache(maxsize=1)
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

@lru_cache(maxsize=1)
def get_vectorstore():
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=get_embeddings()
    )

def get_retriever(category: str = None, k: int = 4):
    vectorstore = get_vectorstore()
    search_kwargs = {"k": k}
    if category and category != "unknown":
        search_kwargs["filter"] = {"category": category}
    return vectorstore.as_retriever(search_kwargs=search_kwargs)

@lru_cache(maxsize=1)
def load_retriever():
    return get_retriever()

retriever = load_retriever()


def resolve_doc_path(source: str, category: str = "") -> str:
    """
    Resolves document source paths to valid absolute paths pointing to markdown files on disk.
    """
    if not source:
        return ""
    base = os.path.abspath(BASE_DIR)

    # Direct path match
    if os.path.exists(source) and os.path.isfile(source):
        return os.path.abspath(source)

    # Clean up relative path markers
    clean_rel = source.replace("..\\", "").replace("../", "").replace("\\", "/")
    candidate2 = os.path.join(base, clean_rel)
    if os.path.exists(candidate2) and os.path.isfile(candidate2):
        return os.path.abspath(candidate2)

    # Category subfolder match: data/docs/<category>/<filename>
    filename = os.path.basename(source)
    if category:
        candidate3 = os.path.join(base, "data", "docs", category, filename)
        if os.path.exists(candidate3) and os.path.isfile(candidate3):
            return os.path.abspath(candidate3)

    # Recursive glob search under data/docs
    matches = glob.glob(os.path.join(base, "data", "docs", "**", filename), recursive=True)
    if matches and os.path.isfile(matches[0]):
        return os.path.abspath(matches[0])

    return os.path.abspath(candidate2)


def build_citation(doc: Any, score: float = 0.85) -> Dict[str, Any]:
    """
    Extracts structured citation metadata from a retrieved Document:
    {title, category, snippet, score, source}
    """
    raw_source = doc.metadata.get("source", "")
    category = doc.metadata.get("category", "")
    content = doc.page_content or ""

    # Title extraction from first line or filename
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    first_line = lines[0] if lines else ""
    title = first_line.lstrip("#").strip() if first_line else ""
    if not title or len(title) > 80:
        base = os.path.basename(raw_source)
        title = os.path.splitext(base)[0].replace("_", " ").title() if base else "Support Knowledge Base"

    # Category normalization
    if not category and len(lines) > 2:
        for i, l in enumerate(lines[:5]):
            if "category" in l.lower() and i + 1 < len(lines):
                category = lines[i+1].strip()
                break
    if not category:
        category = "general"

    # Supporting snippet extraction
    snippet = ""
    lower = content.lower()
    if "## solution" in lower:
        parts = content.split("## Solution")
        if len(parts) > 1:
            sol_lines = [l.strip() for l in parts[1].split("\n\n")[0].splitlines() if l.strip()]
            snippet = " ".join(sol_lines[:3])
    elif "## problem" in lower:
        parts = content.split("## Problem")
        if len(parts) > 1:
            prob_lines = [l.strip() for l in parts[1].split("\n\n")[0].splitlines() if l.strip()]
            snippet = " ".join(prob_lines[:2])

    if not snippet:
        body = lines[1:] if len(lines) > 1 else lines
        snippet = " ".join(body[:3])[:280]

    snippet = snippet.strip()
    if len(snippet) > 280:
        snippet = snippet[:277] + "..."

    resolved_source = resolve_doc_path(raw_source, category)

    return {
        "title": title,
        "category": category,
        "snippet": snippet,
        "score": max(0.0, min(1.0, round(float(score), 4))) if isinstance(score, (int, float)) else 0.85,
        "source": resolved_source
    }


def retrieve_with_scores(query: str, category: str = None, k: int = 4) -> List[Tuple[Any, float]]:
    """
    Queries Chroma vectorstore with similarity search and relevance scores.
    Falls back to standard search if relevance score computation raises an error.
    """
    vs = get_vectorstore()
    filter_dict = {"category": category} if category and category != "unknown" else None
    try:
        results = vs.similarity_search_with_relevance_scores(query, k=k, filter=filter_dict)
    except Exception:
        docs = vs.similarity_search(query, k=k, filter=filter_dict)
        results = [(d, 0.85) for d in docs]
    return results



