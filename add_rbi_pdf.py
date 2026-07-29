import sqlite3
import sys
import shutil
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "db", "compliance.db")
RBI_DIR  = os.path.join(BASE_DIR, "data", "rbi")

def list_pending_rbi():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, url FROM document_queue WHERE source='rbi' AND file_path IS NULL")
    rows = c.fetchall()
    conn.close()
    return rows

def attach_pdf(doc_id, pdf_source_path):
    if not os.path.exists(pdf_source_path):
        print(f"File not found: {pdf_source_path}")
        return

    os.makedirs(RBI_DIR, exist_ok=True)
    filename = f"rbi_{doc_id}.pdf"
    dest_path = os.path.join(RBI_DIR, filename)
    shutil.copy(pdf_source_path, dest_path)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE document_queue SET file_path=? WHERE id=?", (dest_path, doc_id))
    conn.commit()
    conn.close()
    print(f"Attached {dest_path} to document_queue id={doc_id}")

if __name__ == "__main__":
    pending = list_pending_rbi()
    if not pending:
        print("No pending RBI circulars without a file.")
        sys.exit()

    print("Pending RBI circulars waiting for a PDF:\n")
    for doc_id, title, url in pending:
        print(f"  [{doc_id}] {title}")
        print(f"       {url}\n")

    doc_id = input("Enter the ID to attach a PDF to: ").strip()
    pdf_path = input("Enter the full path to the PDF file on your computer: ").strip().strip('"')
    attach_pdf(int(doc_id), pdf_path)