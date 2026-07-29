import sqlite3

conn = sqlite3.connect('db/compliance.db')
c = conn.cursor()

c.execute("DROP TABLE IF EXISTS document_chunks_child")
c.execute("DROP TABLE IF EXISTS document_chunks")
c.execute("DROP TABLE IF EXISTS policy_chunks_child")
c.execute("DROP TABLE IF EXISTS policy_chunks")
print("Dropped old chunk tables (parent + child, circulars + policies)")

c.execute("UPDATE document_queue SET status='pending' WHERE status='processed'")
print(f"Reset {c.rowcount} document_queue rows to pending")

conn.commit()
conn.close()
print("Reset complete — ready to reprocess with parent-child chunking.")