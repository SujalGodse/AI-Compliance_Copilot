#!/usr/bin/env python3
"""
Runs the compliance pipeline for all pending circulars.
"""
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

# Check pending
c.execute("SELECT id, title FROM document_queue WHERE status='pending'")
pending = c.fetchall()
print(f"Pending circulars: {len(pending)}")
for r in pending:
    print(f"  ID={r['id']}: {r['title'][:60]}")
conn.close()

if len(pending) == 0:
    print("No pending circulars. Pipeline run not needed.")
    sys.exit(0)

print("\nStarting pipeline run...")
try:
    from agents import run_pipeline
    result = run_pipeline()
    print(f"Pipeline result: {result}")
except Exception as e:
    print(f"Pipeline error: {e}")
    import traceback
    traceback.print_exc()
