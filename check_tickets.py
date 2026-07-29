import sqlite3
import json

conn = sqlite3.connect('db/compliance.db')
c    = conn.cursor()

c.execute("SELECT ticket_id, regulator, domain, drift_score, priority, created_at FROM compliance_tickets")
rows = c.fetchall()

print(f"\nTotal tickets: {len(rows)}")
print("=" * 60)
for r in rows:
    print(f"ID       : {r[0]}")
    print(f"Regulator: {r[1]}")
    print(f"Domain   : {r[2]}")
    print(f"Score    : {r[3]}")
    print(f"Priority : {r[4]}")
    print(f"Created  : {r[5]}")
    print("-" * 60)

conn.close()