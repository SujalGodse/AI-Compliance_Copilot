import sqlite3
conn = sqlite3.connect('db/compliance.db')
c = conn.cursor()
c.execute("DELETE FROM policy_chunks")
print(f"Deleted {c.rowcount} policy chunks")
conn.commit()
conn.close()