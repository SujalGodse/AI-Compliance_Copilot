import sqlite3

conn = sqlite3.connect('db/compliance.db')
c = conn.cursor()
c.execute("DELETE FROM document_queue WHERE source='rbi'")
print(f"Deleted {c.rowcount} RBI rows from document_queue")
conn.commit()
conn.close()