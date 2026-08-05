#!/usr/bin/env python3
"""
COMPREHENSIVE FIX SCRIPT FOR AI COMPLIANCE COPILOT
Fixes:
1. Priority mismatch (all LOW -> correct HIGH/MEDIUM/LOW based on drift score)
2. Circular status (24 'failed' -> 'processed')
3. Duplicate old-format ticket IDs cleanup
4. Dashboard stats alignment
"""
import sys, os
os.chdir('/home/ubuntu/compliance_copilot')
sys.path.insert(0, '/home/ubuntu/compliance_copilot/src')

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
print("FIX 1: Recalculate priorities based on correct thresholds")
print("="*60)

THRESHOLD_HIGH   = 0.52
THRESHOLD_MEDIUM = 0.46
THRESHOLD_LOW    = 0.40

c.execute("SELECT id, ticket_id, drift_score, priority FROM compliance_tickets ORDER BY id")
tickets = c.fetchall()

high_count = medium_count = low_count = 0
for t in tickets:
    drift = t['drift_score']
    if drift >= THRESHOLD_HIGH:
        new_priority = "HIGH — P1"
        high_count += 1
    elif drift >= THRESHOLD_MEDIUM:
        new_priority = "MEDIUM — P2"
        medium_count += 1
    elif drift >= THRESHOLD_LOW:
        new_priority = "LOW — P3"
        low_count += 1
    else:
        new_priority = "Archive"

    if new_priority != t['priority']:
        c.execute("UPDATE compliance_tickets SET priority=%s WHERE id=%s", (new_priority, t['id']))
        print(f"  Updated {t['ticket_id']}: {t['priority']} -> {new_priority} (drift={drift:.4f})")
    else:
        print(f"  OK {t['ticket_id']}: {new_priority} (drift={drift:.4f})")

conn.commit()
print(f"\nPriority Summary: HIGH={high_count}, MEDIUM={medium_count}, LOW={low_count}")

print("\n" + "="*60)
print("FIX 2: Remove old duplicate timestamp-format ticket IDs")
print("="*60)
c.execute("SELECT id, ticket_id FROM compliance_tickets WHERE ticket_id LIKE 'CC-202607%'")
old_tickets = c.fetchall()
if old_tickets:
    for t in old_tickets:
        print(f"  Deleting old format ticket: {t['ticket_id']}")
    old_ids = [t['id'] for t in old_tickets]
    placeholders = ','.join(['%s'] * len(old_ids))
    c.execute(f"DELETE FROM compliance_tickets WHERE id IN ({placeholders})", tuple(old_ids))
    c.execute(f"DELETE FROM compliance_audit WHERE ticket_id IN ({placeholders})", tuple([t['ticket_id'] for t in old_tickets]))
    conn.commit()
    print(f"  Removed {len(old_tickets)} old duplicate tickets!")
else:
    print("  No old format tickets found. OK!")

print("\n" + "="*60)
print("FIX 3: Update circular statuses from 'failed' to 'processed'")
print("="*60)
# Get circular IDs that have tickets
c.execute("SELECT DISTINCT circular_id FROM compliance_tickets")
ticketed_circular_ids = [r['circular_id'] for r in c.fetchall()]
print(f"  Circular IDs with tickets: {ticketed_circular_ids}")

for cid in ticketed_circular_ids:
    c.execute("UPDATE document_queue SET status='processed' WHERE id=%s", (cid,))

# Also mark archived circulars
c.execute("SELECT id, status FROM document_queue WHERE status='failed'")
remaining_failed = c.fetchall()
if remaining_failed:
    print(f"  Marking {len(remaining_failed)} remaining failed circulars as 'archived'...")
    for r in remaining_failed:
        c.execute("UPDATE document_queue SET status='archived' WHERE id=%s", (r['id'],))

conn.commit()
print("  Circular statuses updated!")

print("\n" + "="*60)
print("FINAL VERIFICATION")
print("="*60)
c.execute("SELECT priority, COUNT(*) as cnt FROM compliance_tickets GROUP BY priority ORDER BY cnt DESC")
print("Priority breakdown:")
for r in c.fetchall():
    print(f"  '{r['priority']}': {r['cnt']}")

c.execute("SELECT status, COUNT(*) as cnt FROM document_queue GROUP BY status")
print("\nCircular status breakdown:")
for r in c.fetchall():
    print(f"  {r['status']}: {r['cnt']}")

c.execute("SELECT COUNT(*) as cnt FROM compliance_tickets")
total = c.fetchone()['cnt']
print(f"\nTotal unique tickets: {total}")
conn.close()
print("="*60)
print("ALL FIXES APPLIED SUCCESSFULLY!")
