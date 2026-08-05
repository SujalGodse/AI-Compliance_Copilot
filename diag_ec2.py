#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/ubuntu/compliance_copilot/src')
import os
os.chdir('/home/ubuntu/compliance_copilot')

# Load env manually
with open('/home/ubuntu/compliance_copilot/.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

from db import get_db
conn = get_db()
c = conn.cursor()

print("="*60)
print("TICKETS DIAGNOSTIC")
print("="*60)
c.execute("SELECT ticket_id, drift_score, priority, LENGTH(summary) as sl, LENGTH(change_list) as cl FROM compliance_tickets ORDER BY id")
rows = c.fetchall()
print(f"Total: {len(rows)}")
for r in rows:
    print(f"  {r['ticket_id']} | drift={round(r['drift_score'],4)} | {r['priority']} | summary={r['sl']}ch | change={r['cl']}ch")

print("\nPRIORITY GROUPS:")
c.execute("SELECT priority, COUNT(*) as cnt FROM compliance_tickets GROUP BY priority ORDER BY cnt DESC")
for r in c.fetchall():
    print(f"  '{r['priority']}': {r['cnt']}")

print("\nCIRCULARS STATUS:")
c.execute("SELECT status, COUNT(*) as cnt FROM document_queue GROUP BY status")
for r in c.fetchall():
    print(f"  {r['status']}: {r['cnt']}")

print("\nSAMPLE SUMMARY (first ticket):")
c.execute("SELECT ticket_id, summary FROM compliance_tickets LIMIT 1")
r = c.fetchone()
if r:
    print(f"  {r['ticket_id']}: {(r['summary'] or '')[:200]}")

conn.close()
print("="*60)
