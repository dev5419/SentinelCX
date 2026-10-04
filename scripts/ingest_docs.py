import os
import sys
import glob
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import CHROMA_DIR

def ingest():
    docs_dir = os.path.join(BASE_DIR, "data", "docs")
    categories = ["billing", "login", "refunds", "subscription"]
    
    raw_docs = []
    for cat in categories:
        cat_dir = os.path.join(docs_dir, cat)
        files = glob.glob(os.path.join(cat_dir, "*.md"))
        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            lines = content.strip().splitlines()
            title = lines[0].strip("# ").strip() if lines else os.path.basename(fpath)
            rel_path = os.path.relpath(fpath, BASE_DIR)
            raw_docs.append(Document(
                page_content=content,
                metadata={
                    "source": rel_path,
                    "category": cat,
                    "title": title
                }
            ))

    print(f"Loaded {len(raw_docs)} documents across categories: {categories}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_documents(raw_docs)
    print(f"Split into {len(chunks)} chunks.")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )
    print(f"Successfully ingested {len(chunks)} chunks into Chroma at {CHROMA_DIR}")

if __name__ == "__main__":
    ingest()
