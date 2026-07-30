import sys
import os
import time

sys.path.append("/home/ubuntu/compliance_copilot/src")
from dotenv import load_dotenv
load_dotenv("/home/ubuntu/compliance_copilot/.env")

from processor import extract_pdf_text, clean_text, chunk_text_parent_child, save_policy_chunks

test_pdf = "/home/ubuntu/compliance_copilot/data/policies/customer_acceptance_policy.pdf"
print("============================================================")
print("       TESTING PADDLEOCR EXTRACTION SPEED ON EC2            ")
print("============================================================")

start_t = time.time()
raw = extract_pdf_text(test_pdf)
cleaned = clean_text(raw)
chunks = chunk_text_parent_child(cleaned)
dur = time.time() - start_t

print(f"\n⚡ PADDLEOCR EXTRACTION COMPLETE IN {dur:.2f} SECONDS!")
print(f"   - Extracted Words: {len(cleaned.split())}")
print(f"   - Parent Chunks Generated: {len(chunks)}")

save_policy_chunks("customer_acceptance_policy.pdf", chunks)

from db import get_db
conn = get_db()
c = conn.cursor()
c.execute("SELECT filename, COUNT(*) as chunks, MAX(created_at) as last_updated FROM policy_chunks WHERE filename='customer_acceptance_policy.pdf' GROUP BY filename")
r = c.fetchone()
conn.close()

print(f"\n📊 RDS DATABASE RECORD VERIFICATION:")
print(f"   - Filename: {r['filename']}")
print(f"   - Total Parent Chunks: {r['chunks']}")
print(f"   - Last Updated: {r['last_updated']}")
print("\n============================================================")
print("          PADDLEOCR & RDS CHUNKING FULLY VERIFIED           ")
print("============================================================")
