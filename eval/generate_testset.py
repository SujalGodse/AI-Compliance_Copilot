# ============================================================
# eval/generate_testset.py
# Auto-generates diverse Q&A pairs from real project documents
# using RAGAS's TestsetGenerator, powered by Groq (LLM) and
# Ollama (embeddings) — same stack as the main pipeline.
# ============================================================

import os
import sqlite3
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from langchain_ollama import OllamaEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.testset import TestsetGenerator

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "db", "compliance.db")
OUT_PATH = os.path.join(BASE_DIR, "eval", "generated_testset.csv")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise SystemExit("GROQ_API_KEY not set — add it to your .env file first.")

# ─────────────────────────────────────────
# LOAD A SAMPLED SET OF REAL CHUNKS
# ─────────────────────────────────────────

def load_sample_documents():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    docs = []

    # 2 chunks per policy file — keeps knowledge graph manageable
    c.execute("""
        SELECT filename, chunk_text, chunk_index
        FROM policy_chunks
        WHERE chunk_index IN (0, 1)
        ORDER BY filename, chunk_index
    """)
    for row in c.fetchall():
        docs.append(Document(
            page_content=row["chunk_text"],
            metadata={"filename": row["filename"]}
        ))

    # 1 representative chunk per circular (first chunk — most context)
    c.execute("""
        SELECT title, chunk_text
        FROM document_chunks
        WHERE chunk_index = 0
        ORDER BY doc_id
    """)
    for row in c.fetchall():
        docs.append(Document(
            page_content=row["chunk_text"],
            metadata={"filename": row["title"][:60]}
        ))

    conn.close()
    return docs

# ─────────────────────────────────────────
# GENERATE TESTSET
# ─────────────────────────────────────────

def main():
    print("Loading sample documents from database...")
    docs = load_sample_documents()
    print(f"Loaded {len(docs)} documents for knowledge graph.")

    print("Setting up generator LLM (Groq) and embeddings (Ollama)...")
    generator_llm = LangchainLLMWrapper(
        ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY, temperature=0)
    )
    generator_embeddings = LangchainEmbeddingsWrapper(
        OllamaEmbeddings(model="nomic-embed-text")
    )

    generator = TestsetGenerator(
        llm=generator_llm,
        embedding_model=generator_embeddings
    )

    print("Generating testset (this may take several minutes)...")
    dataset = generator.generate_with_langchain_docs(docs, testset_size=15)

    df = dataset.to_pandas()
    df.to_csv(OUT_PATH, index=False)

    print(f"\nDone. Saved {len(df)} generated questions to {OUT_PATH}")
    print("\nPreview:")
    print(df[["user_input"]].head(15).to_string())

if __name__ == "__main__":
    main()