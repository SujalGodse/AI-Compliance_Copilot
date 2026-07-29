import os
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "db", "compliance.db")
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT id FROM document_queue WHERE source='rbi'")
rbi_ids = [r[0] for r in c.fetchall()]
print(f"Found {len(rbi_ids)} RBI document_queue rows: {rbi_ids}")

if rbi_ids:
    placeholders = ",".join("?" * len(rbi_ids))

    c.execute(f"DELETE FROM document_chunks WHERE doc_id IN ({placeholders})", rbi_ids)
    print(f"Deleted {c.rowcount} document_chunks rows")

    c.execute(f"DELETE FROM compliance_audit WHERE circular_id IN ({placeholders})", rbi_ids)
    print(f"Deleted {c.rowcount} compliance_audit rows")

    c.execute(f"DELETE FROM compliance_tickets WHERE circular_id IN ({placeholders})", rbi_ids)
    print(f"Deleted {c.rowcount} compliance_tickets rows")

c.execute("UPDATE document_queue SET status='pending', file_path=NULL WHERE source='rbi'")
print(f"Reset {c.rowcount} document_queue rows to pending")

conn.commit()
conn.close()

# clean up the bad RBI vectors from ChromaDB
from embeddings import get_collection, COL_CIRCULARS

col = get_collection(COL_CIRCULARS)
all_ids = col.get()["ids"]
rbi_chroma_ids = [i for i in all_ids if i.startswith("rbi_")]
if rbi_chroma_ids:
    col.delete(ids=rbi_chroma_ids)
    print(f"Deleted {len(rbi_chroma_ids)} RBI vectors from ChromaDB")
else:
    print("No RBI vectors found in ChromaDB")

print("RBI reset complete — ready to re-ingest.")