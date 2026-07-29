import sqlite3
conn = sqlite3.connect('db/compliance.db')
c = conn.cursor()
c.execute("DROP TABLE IF EXISTS document_chunks")
c.execute("DROP TABLE IF EXISTS document_queue")
print("Database cleared completely")
conn.commit()
conn.close()