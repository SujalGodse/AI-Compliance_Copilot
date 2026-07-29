import sqlite3
conn = sqlite3.connect('db/compliance.db')
rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables in database:")
for r in rows:
    print(f"  {r[0]}")
conn.close()