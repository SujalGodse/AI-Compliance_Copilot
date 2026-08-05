#!/bin/bash
curl -s http://localhost:8000/api/tickets > /tmp/tickets.json
python3 << 'PYEOF'
import json
d = json.load(open("/tmp/tickets.json"))
ts = d["tickets"]
print(f"Total Tickets: {len(ts)}")
for t in ts:
    print(f"  {t['ticket_id']} | drift={t['drift_score']:.4f} | priority={t['priority']} | summary_len={len(t.get('summary',''))}")
PYEOF
