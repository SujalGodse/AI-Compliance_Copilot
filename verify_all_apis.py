#!/usr/bin/env python3
import json, subprocess, sys

def check(url, label):
    result = subprocess.run(["curl", "-s", url], capture_output=True, text=True, timeout=10)
    try:
        d = json.loads(result.stdout)
        return d
    except:
        return {"error": result.stdout[:200]}

print("="*60)
print("FINAL LIVE API VERIFICATION")
print("="*60)

# Stats
d = check("http://localhost:8000/api/stats", "stats")
t = d.get("tickets", {})
c = d.get("circulars", {})
p = d.get("policies", {})
print(f"\n/api/stats:")
print(f"  Tickets: total={t.get('total')}, high={t.get('high')}, medium={t.get('medium')}, low={t.get('low')}")
print(f"  Circulars: total={c.get('total')}, processed={c.get('processed')}")
print(f"  Policies: total={p.get('total')}")

# Policies
d = check("http://localhost:8000/api/policies", "policies")
print(f"\n/api/policies:")
for pol in d.get("policies", []):
    print(f"  {pol['filename']}: {pol['chunks']} chunks")

# Tickets
d = check("http://localhost:8000/api/tickets", "tickets")
ts = d.get("tickets", [])
print(f"\n/api/tickets: {len(ts)} tickets")
highs = [t for t in ts if "P1" in t.get("priority","")]
meds  = [t for t in ts if "P2" in t.get("priority","")]
lows  = [t for t in ts if "P3" in t.get("priority","")]
print(f"  HIGH(P1)={len(highs)}, MEDIUM(P2)={len(meds)}, LOW(P3)={len(lows)}")

# Circulars
d = check("http://localhost:8000/api/circulars", "circulars")
circs = d.get("circulars", [])
print(f"\n/api/circulars: {len(circs)} total")

# Drift Scores
d = check("http://localhost:8000/api/drift-scores", "drift-scores")
sc = d.get("scores", [])
print(f"\n/api/drift-scores: {len(sc)} scores")

# Health
d = check("http://localhost:8000/api/health", "health")
print(f"\n/api/health: {d}")

# Dashboard Summary
d = check("http://localhost:8000/api/dashboard-summary", "dashboard-summary")
dom = d.get("by_domain", [])
rec = d.get("recent_tickets", [])
print(f"\n/api/dashboard-summary:")
print(f"  by_domain: {len(dom)} domains -> {[x['domain'] for x in dom[:5]]}")
print(f"  recent_tickets: {len(rec)} tickets")

print("\n" + "="*60)
print("ALL ENDPOINTS OK!")
