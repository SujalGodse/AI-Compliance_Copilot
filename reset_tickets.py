import sqlite3
conn = sqlite3.connect('db/compliance.db')
c    = conn.cursor()
c.execute("DELETE FROM compliance_tickets")
c.execute("DELETE FROM compliance_audit")
conn.commit()
conn.close()
print("Tickets and audit cleared.")