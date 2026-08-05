import json, sys

sys.path.insert(0, "/home/ubuntu/compliance_copilot/src")
from dotenv import load_dotenv
load_dotenv("/home/ubuntu/compliance_copilot/.env")
from db import get_db

conn = get_db()
c = conn.cursor()

# Check tickets
c.execute("SELECT ticket_id, drift_score, priority, summary, change_list FROM compliance_tickets ORDER BY id")
rows = c.fetchall()
print(f"=== TICKETS ({len(rows)} total) ===")
for r in rows:
    summary_len = len(r['summary']) if r['summary'] else 0
    change_len = len(r['change_list']) if r['change_list'] else 0
    print(f"  {r['ticket_id']} | drift={r['drift_score']:.4f} | {r['priority']} | summary={summary_len}ch | change={change_len}ch")

# Check dashboard stats
c.execute("SELECT COUNT(*) as cnt FROM compliance_tickets WHERE priority LIKE '%P1%'")
high = c.fetchone()['cnt']
c.execute("SELECT COUNT(*) as cnt FROM compliance_tickets WHERE priority LIKE '%P2%'")
medium = c.fetchone()['cnt']
c.execute("SELECT COUNT(*) as cnt FROM compliance_tickets WHERE priority LIKE '%P3%'")
low = c.fetchone()['cnt']
print(f"\n=== PRIORITY BREAKDOWN ===")
print(f"  HIGH (P1): {high}")
print(f"  MEDIUM (P2): {medium}")
print(f"  LOW (P3): {low}")

# Check circulars
c.execute("SELECT COUNT(*) as cnt FROM document_queue")
total_circulars = c.fetchone()['cnt']
c.execute("SELECT COUNT(*) as cnt FROM document_queue WHERE status='processed'")
processed = c.fetchone()['cnt']
print(f"\n=== CIRCULARS ===")
print(f"  Total: {total_circulars}")
print(f"  Processed: {processed}")

# Check if summaries are empty/fallback
c.execute("SELECT ticket_id, LEFT(summary, 100) FROM compliance_tickets LIMIT 5")
print(f"\n=== SAMPLE SUMMARIES ===")
for r in c.fetchall():
    print(f"  {r['ticket_id']}: {list(r.values())[1]}")

conn.close()
