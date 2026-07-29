# verify_setup.py
import sys

def check(label, fn):
    try:
        result = fn()
        print(f"  OK  {label}: {result}")
    except Exception as e:
        print(f"  FAIL  {label}: {e}")

print("\n AI Compliance Copilot - Setup Verification\n")

check("Python version", lambda: sys.version.split()[0])

def test_ollama_llm():
    import requests
    r = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3.1",
        "prompt": "Reply with only the word: WORKING",
        "stream": False
    }, timeout=60)
    return r.json()["response"].strip()
check("Ollama LLM (llama3.1)", test_ollama_llm)

def test_ollama_embed():
    import requests
    r = requests.post("http://localhost:11434/api/embeddings", json={
        "model": "nomic-embed-text",
        "prompt": "RBI circular on KYC norms"
    }, timeout=30)
    vec = r.json()["embedding"]
    return f"vector length = {len(vec)}"
check("Ollama embeddings (nomic-embed-text)", test_ollama_embed)

def test_chroma():
    import chromadb
    client = chromadb.Client()
    col = client.create_collection("test_col")
    col.add(documents=["RBI KYC circular"], ids=["doc1"])
    res = col.query(query_texts=["KYC"], n_results=1)
    client.delete_collection("test_col")
    return f"stored and retrieved {len(res['documents'][0])} doc"
check("ChromaDB", test_chroma)

def test_spacy():
    import spacy
    nlp = spacy.load("en_core_web_sm")
    doc = nlp("RBI issued a circular on KYC norms.")
    ents = [(e.text, e.label_) for e in doc.ents]
    return f"NER found {len(ents)} entities"
check("spaCy (en_core_web_sm)", test_spacy)

def test_pymupdf():
    import fitz
    return f"pymupdf version {fitz.version[0]}"
check("pymupdf", test_pymupdf)

print("\nIf all OK above - your stack is ready!\n")