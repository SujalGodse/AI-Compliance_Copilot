import sqlite3

conn = sqlite3.connect('db/compliance.db')
cur = conn.cursor()
rows = cur.execute("SELECT id, chunk_text FROM document_chunks WHERE chunk_text LIKE '%NISM%' OR chunk_text LIKE '%certification%' OR chunk_text LIKE '%adviser%'").fetchall()
for r in rows:
    print('Match ID:', r[0], '->', r[1][:120])
print('Total matches in document_chunks:', len(rows))
conn.close()
