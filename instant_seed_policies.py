import os
import sys
import json
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from db import get_db, init_all_tables
from processor import save_policy_chunks
from embeddings import get_collection, get_embeddings_batch, COL_POLICIES

print("============================================================")
print("  🚀 INSTANT 0.5s POLICY INDEXER FOR AWS RDS & MILVUS       ")
print("============================================================")

json_path = os.path.join(BASE_DIR, "precalculated_policy_chunks.json")
if not os.path.exists(json_path):
    print("❌ precalculated_policy_chunks.json missing!")
    sys.exit(1)

with open(json_path, "r") as jf:
    policy_data = json.load(jf)

init_all_tables()
col_p = None
try:
    col_p = get_collection(COL_POLICIES)
except Exception as e:
    print(f"Milvus Notice: {e}")

# Clear all old policy chunks in PostgreSQL
conn = get_db()
c = conn.cursor()
c.execute("TRUNCATE TABLE policy_chunks, policy_chunks_child RESTART IDENTITY CASCADE;")
conn.commit()
conn.close()

for fname, chunks in policy_data.items():
    print(f"   • Inserting {fname} ({len(chunks)} Parent Chunks)...")
    save_policy_chunks(fname, chunks)

    if col_p:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM policy_chunks WHERE filename=%s", (fname,))
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
                        "filename": fname
                    })
            if records:
                col_p.insert(records)
                col_p.flush()
                print(f"     ✅ Embedded {len(records)} Child Vectors into Milvus!")

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
