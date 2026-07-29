import sqlite3

conn = sqlite3.connect('db/compliance.db')
c = conn.cursor()
c.execute("SELECT id, title, url, file_path, status FROM document_queue WHERE source='rbi'")
rows = c.fetchall()
conn.close()

print(f"RBI rows in queue: {len(rows)}")
for r in rows:
    print(r)