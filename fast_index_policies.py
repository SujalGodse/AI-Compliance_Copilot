import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from db import get_db, init_all_tables
from processor import extract_pdf_text, save_policy_chunks
from embeddings import get_collection, get_embeddings_batch, COL_POLICIES

def chunk_fast(text, parent_words=800, child_words=150):
    words = text.split()
    parents = []
    for i in range(0, len(words), parent_words):
        p_words = words[i:i+parent_words]
        p_text = " ".join(p_words)
        children = []
        for j in range(0, len(p_words), child_words):
            c_words = p_words[j:j+child_words]
            children.append(" ".join(c_words))
        parents.append({"parent_text": p_text, "children": children})
    return parents

print("============================================================")
print("  🚀 FAST MEMORY-SAFE POLICY INDEXER FOR AWS RDS & MILVUS   ")
print("============================================================")

init_all_tables()
col_p = None
try:
    col_p = get_collection(COL_POLICIES)
except Exception as e:
    print(f"Milvus Notice: {e}")

policies_dir = os.path.join(BASE_DIR, "data", "policies")
policy_files = [
    "customer_acceptance_policy.pdf",
    "customer_protection_policy.pdf",
    "deposit_policy.pdf",
    "fair_practices_code.pdf",
    "grievance_redressal_policy.pdf"
]

for idx, p_file in enumerate(policy_files, 1):
    p_path = os.path.join(policies_dir, p_file)
    if not os.path.exists(p_path):
        print(f"   [{idx}/{len(policy_files)}] ⚠️ File not found: {p_path}")
        continue

    print(f"   [{idx}/{len(policy_files)}] Processing {p_file}...")
    try:
        raw_text = extract_pdf_text(p_path)
        chunks = chunk_fast(raw_text)

        # Delete old rows for this file in PostgreSQL
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM policy_chunks WHERE filename=%s", (p_file,))
        conn.commit()
        conn.close()

        save_policy_chunks(p_file, chunks)
        print(f"     ✅ Saved {len(chunks)} Parent Chunks into AWS RDS PostgreSQL!")

        # Retrieve child chunks and embed into Milvus
        if col_p:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT id FROM policy_chunks WHERE filename=%s", (p_file,))
            p_ids = [r['id'] for r in c.fetchall()]

            child_rows = []
            if p_ids:
                placeholders = ", ".join(["%s"] * len(p_ids))
                c.execute(f"SELECT id, parent_id, child_index, chunk_text FROM policy_chunks_child WHERE parent_id IN ({placeholders})", tuple(p_ids))
                child_rows = [dict(r) for r in c.fetchall()]
            conn.close()

            if child_rows:
                texts = [r['chunk_text'] for r in child_rows]
                vectors = get_embeddings_batch(texts)

                records = []
                for i, r in enumerate(child_rows):
                    if i < len(vectors) and vectors[i]:
                        milvus_id = f"policy_{r['parent_id']}_{r['child_index']}"
                        records.append({
                            "id": milvus_id,
                            "vector": vectors[i],
                            "document": r['chunk_text'][:65535],
                            "doc_id": "",
                            "parent_id": str(r['parent_id']),
                            "source": "",
                            "title": "",
                            "child_index": str(r['child_index']),
                            "domain": "General",
                            "filename": p_file
                        })
                if records:
                    col_p.insert(records)
                    col_p.flush()
                    print(f"     ✅ Embedded {len(records)} Child Vectors into Milvus!")
    except Exception as err:
        print(f"     ❌ Error indexing {p_file}: {err}")

print("\n============================================================")
print("     POSTGRESQL POLICY_CHUNKS FINAL VERIFICATION:")
print("============================================================")
conn = get_db()
c = conn.cursor()
c.execute("SELECT filename, COUNT(*) as chunks FROM policy_chunks GROUP BY filename ORDER BY filename")
rows = c.fetchall()
for r in rows:
    print(f"  • {r['filename']}: {r['chunks']} chunks")
print("============================================================")
conn.close()
