import sqlite3
conn = sqlite3.connect('db/compliance.db')
c = conn.cursor()

print("=== FAILED DOCUMENTS ===")
c.execute("SELECT id, source, title FROM document_queue WHERE status='failed'")
for row in c.fetchall():
    print(f"ID {row[0]} [{row[1].upper()}]: {row[2]}")

print("\n=== CHUNKS SUMMARY ===")
c.execute("SELECT source, COUNT(*), AVG(word_count) FROM document_chunks GROUP BY source")
for row in c.fetchall():
    print(f"  {row[0].upper()}: {row[1]} chunks, avg {int(row[2])} words each")

print("\n=== STATUS SUMMARY ===")
c.execute("SELECT status, COUNT(*) FROM document_queue GROUP BY status")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]} documents")

conn.close()