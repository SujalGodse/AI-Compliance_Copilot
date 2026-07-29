import sqlite3
conn = sqlite3.connect('db/compliance.db')
c = conn.cursor()
c.execute("DELETE FROM document_chunks WHERE source='rbi'")
print(f"Deleted {c.rowcount} RBI chunks")
c.execute("UPDATE document_queue SET status='pending' WHERE source='rbi'")
print(f"Reset {c.rowcount} RBI documents to pending")
conn.commit()
conn.close()