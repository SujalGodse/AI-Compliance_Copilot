#!/usr/bin/env python3
import sys, os
os.chdir('/home/ubuntu/compliance_copilot')
sys.path.insert(0, '/home/ubuntu/compliance_copilot/src')

with open('/home/ubuntu/compliance_copilot/.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

from db import get_db
conn = get_db()
c = conn.cursor()

# Check all circulars
c.execute("SELECT id, title, status FROM document_queue ORDER BY id")
rows = c.fetchall()
print(f"=== ALL CIRCULARS ({len(rows)} total) ===")
for r in rows:
    print(f"  ID={r['id']} | {r['status']} | {r['title'][:60]}")

# Get IDs missing tickets
c.execute("SELECT DISTINCT circular_id FROM compliance_tickets")
ticketed = set(r['circular_id'] for r in c.fetchall())
print(f"\nCircular IDs with tickets: {sorted(ticketed)}")

# Archived circulars without tickets
c.execute("SELECT id, title FROM document_queue WHERE status='archived'")
archived = c.fetchall()
print(f"\nArchived circulars (no tickets): {len(archived)}")
for r in archived:
    print(f"  ID={r['id']}: {r['title'][:60]}")

# Mark them back to 'pending' to reprocess
print("\nResetting archived circulars to 'pending' for pipeline rerun...")
c.execute("UPDATE document_queue SET status='pending' WHERE status='archived'")
conn.commit()
print("Done! These circulars are now ready for pipeline processing.")

c.execute("SELECT status, COUNT(*) as cnt FROM document_queue GROUP BY status")
print("\nUpdated status counts:")
for r in c.fetchall():
    print(f"  {r['status']}: {r['cnt']}")

conn.close()
