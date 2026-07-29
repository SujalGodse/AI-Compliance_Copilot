# ============================================================
# migrate_to_rds.py
# One-time migration: SQLite → Amazon RDS PostgreSQL
#
# Run ONCE after creating your RDS instance:
#   python migrate_to_rds.py
# ============================================================

import os
import sys
import json
import sqlite3
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, "db", "compliance.db")

# ── RDS connection ─────────────────────────────────────────
PG_CONFIG = {
    "host"    : os.getenv("RDS_HOST"),
    "port"    : int(os.getenv("RDS_PORT", "5432")),
    "dbname"  : os.getenv("RDS_DB",       "compliance"),
    "user"    : os.getenv("RDS_USER",     "admin"),
    "password": os.getenv("RDS_PASSWORD", ""),
}

def migrate():
    print("=" * 60)
    print("SQLite -> RDS PostgreSQL Migration")
    print("=" * 60)

    # ── Connect to both DBs ──────────────────────────────
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sq = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(**PG_CONFIG,
                               cursor_factory=psycopg2.extras.RealDictCursor)
    pg = pg_conn.cursor()

    # ── Create tables first ──────────────────────────────
    sys.path.insert(0, os.path.join(BASE_DIR, "src"))
    from db import init_all_tables
    init_all_tables()
    print("✅ Tables created on RDS")

    # ── Migrate document_queue ───────────────────────────
    try:
        sq.execute("SELECT * FROM document_queue")
        rows = sq.fetchall()
        count = 0
        for row in rows:
            row = dict(row)
            pg.execute("""
                INSERT INTO document_queue
                    (source, title, url, file_path, sha256, status)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (sha256) DO NOTHING
            """, (row['source'], row['title'], row['url'],
                  row['file_path'], row['sha256'], row['status']))
            count += 1
        pg_conn.commit()
        print(f"✅ document_queue:     {count} rows migrated")
    except Exception as e:
        print(f"⚠️  document_queue skipped: {e}")

    # ── Migrate compliance_tickets ───────────────────────
    try:
        sq.execute("SELECT * FROM compliance_tickets")
        rows = sq.fetchall()
        count = 0
        for row in rows:
            row = dict(row)
            pg.execute("""
                INSERT INTO compliance_tickets
                    (ticket_id, circular_id, source, title, regulator,
                     domain, doc_type, drift_score, semantic_score,
                     policy_score, entity_score, priority,
                     affected_policies, summary, change_list, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (ticket_id) DO NOTHING
            """, (
                row['ticket_id'], row['circular_id'], row['source'],
                row['title'], row['regulator'], row['domain'],
                row['doc_type'], row['drift_score'], row['semantic_score'],
                row['policy_score'], row['entity_score'], row['priority'],
                row['affected_policies'], row['summary'],
                row['change_list'], row['status']
            ))
            count += 1
        pg_conn.commit()
        print(f"✅ compliance_tickets: {count} rows migrated")
    except Exception as e:
        print(f"⚠️  compliance_tickets skipped: {e}")

    # ── Migrate compliance_audit ─────────────────────────
    try:
        sq.execute("SELECT * FROM compliance_audit")
        rows = sq.fetchall()
        count = 0
        for row in rows:
            row = dict(row)
            pg.execute("""
                INSERT INTO compliance_audit
                    (ticket_id, circular_id, title, regulator, domain,
                     drift_score, priority, route,
                     agent1_out, agent2_out, agent3_out)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                row['ticket_id'], row['circular_id'], row['title'],
                row['regulator'], row['domain'], row['drift_score'],
                row['priority'], row['route'],
                json.dumps(row['agent1_out']) if row['agent1_out'] else None,
                json.dumps(row['agent2_out']) if row['agent2_out'] else None,
                json.dumps(row['agent3_out']) if row['agent3_out'] else None,
            ))
            count += 1
        pg_conn.commit()
        print(f"✅ compliance_audit:   {count} rows migrated")
    except Exception as e:
        print(f"⚠️  compliance_audit skipped: {e}")

    # ── Done ─────────────────────────────────────────────
    sqlite_conn.close()
    pg_conn.close()

    print("=" * 60)
    print("Migration complete! Your RDS database is ready.")
    print("=" * 60)

if __name__ == "__main__":
    migrate()
