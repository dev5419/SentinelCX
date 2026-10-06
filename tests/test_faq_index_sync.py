"""Offline regression checks for automatic FAQ indexing and answer routing."""
import ast
import glob
import hashlib
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_function(path, name, namespace):
    # Load the production function without initializing models or live services.
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


class Document:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata


class Splitter:
    def __init__(self, **kwargs):
        pass

    def split_documents(self, docs):
        return docs


class Store:
    def __init__(self):
        self.docs = {}
        self.writes = 0

    def get(self, where):
        matching = {k: d for k, d in self.docs.items() if d.metadata["source"] == where["source"]}
        return {"ids": list(matching), "metadatas": [d.metadata for d in matching.values()]}

    def add_documents(self, docs, ids):
        self.writes += 1
        self.docs.update(zip(ids, docs))

    def delete(self, ids):
        for key in ids:
            del self.docs[key]


class FAQRegressionTests(unittest.TestCase):
    def test_missing_and_changed_articles_are_indexed_without_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            article = Path(directory) / "data/docs/refunds/policy.md"
            article.parent.mkdir(parents=True)
            article.write_text("# Policy\nReturn within 14 days.", encoding="utf-8")
            sync = load_function(ROOT / "rag/retriever.py", "sync_documents", {
                "os": os, "glob": glob, "hashlib": hashlib, "BASE_DIR": directory,
                "Document": Document, "RecursiveCharacterTextSplitter": Splitter,
            })
            store = Store()
            sync(store)
            self.assertEqual(len(store.docs), 1)
            sync(store)
            self.assertEqual(store.writes, 1)
            article.write_text("# Policy\nUpdated return policy.", encoding="utf-8")
            sync(store)
            self.assertEqual(len(store.docs), 1)
            self.assertIn("Updated", next(iter(store.docs.values())).page_content)

    def test_typed_and_simulator_faq_return_grounded_answer(self):
        article = ROOT / "data/docs/refunds/return_refund_policy.md"
        content = article.read_text(encoding="utf-8")
        doc = Document(content, {"source": str(article), "category": "refunds"})
        answer = "Return requests must be submitted within 14 days of delivery. Eligible refunds up to Rs 2,000 are automatically approved."
        namespace = {
            "SupportState": dict, "Dict": dict, "Any": object, "time": time,
            "normalize_to_english": lambda q, lang: q,
            "retrieve_with_scores": lambda *args, **kwargs: [(doc, 0.9)],
            "build_citation": lambda d, s: {"title": "Return policy", "source": str(article), "score": s},
            "LLM": SimpleNamespace(invoke=lambda prompt: SimpleNamespace(content=answer)),
            "is_grounded": lambda a, c: "14 days" in c and "Rs 2,000" in c,
        }
        route = load_function(ROOT / "core/graph.py", "route_from_triage", namespace)
        rag = load_function(ROOT / "core/graph.py", "rag_node", namespace)
        grounding = load_function(ROOT / "core/graph.py", "grounding_node", namespace)
        for query in ["What is your return policy?",
                      "What is the return and refund policy window for delivered items?"]:
            state = {"user_query": query, "intent": "faq", "intent_confidence": 0.9,
                     "is_transactional": False, "language": "en"}
            self.assertEqual(route(state), "rag")
            state.update(rag(state))
            state.update(grounding(state))
            self.assertEqual(state["action"], "answer")
            self.assertTrue(state["grounded"])
            self.assertFalse(state["force_escalate"])
            self.assertIn("14 days", state["answer"])
            self.assertTrue(state["retrieved_docs"])


if __name__ == "__main__":
    unittest.main()
