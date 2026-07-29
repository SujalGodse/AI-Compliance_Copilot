import sqlite3

conn = sqlite3.connect('db/compliance.db')
c = conn.cursor()
c.execute("DELETE FROM document_queue WHERE source='rbi'")
print(f"Deleted {c.rowcount} RBI document_queue rows")
conn.commit()
conn.close()