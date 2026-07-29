import urllib.request
import ssl
import os

# create policies folder
os.makedirs("data/policies", exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

policies = {
    "bank_of_india_corporate_governance_2025.pdf":
        "https://bankofindia.bank.in/documents/20121/25744421/Corporate-Governance-Policy-2025.pdf",
    "bank_of_india_deposit_policy_2024.pdf":
        "https://bankofindia.bank.in/documents/20121/25744421/Deposit-Policy-2024-25-Revised.pdf",
    "bank_of_india_disclosure_policy_2024.pdf":
        "https://bankofindia.bank.in/documents/20121/22604236/DisclosurePolicy-29.02.2024.pdf",
}

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

for filename, url in policies.items():
    save_path = f"data/policies/{filename}"
    print(f"Downloading: {filename}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            content = r.read()
        with open(save_path, "wb") as f:
            f.write(content)
        size = os.path.getsize(save_path) // 1024
        print(f"  Saved: {save_path} ({size} KB)")
    except Exception as e:
        print(f"  Failed: {e}")

print("\nDone!")