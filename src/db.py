# ============================================================
# src/db.py
# Shared Database Connection — RDS PostgreSQL
#
# Drop-in replacement for sqlite3 across all modules.
# All modules import get_db() from here.
# ============================================================

import os
import logging
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

# ── Connection config (from .env) ──────────────────────────
_DB_CONFIG = {
    "host"    : os.getenv("RDS_HOST",     "localhost"),
    "port"    : int(os.getenv("RDS_PORT", "5432")),
    "dbname"  : os.getenv("RDS_DB",       "compliance"),
    "user"    : os.getenv("RDS_USER",     "admin"),
    "password": os.getenv("RDS_PASSWORD", ""),
    "connect_timeout": 10,
}

def get_db():
    """Return a psycopg2 connection with RealDictCursor (dict-like rows)."""
    conn = psycopg2.connect(
        **_DB_CONFIG,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    return conn


def init_all_tables():
    """
    Create all tables on first run.
    Safe to call multiple times (CREATE TABLE IF NOT EXISTS).
    PostgreSQL equivalents of the SQLite schema.
    """
    conn = get_db()
    cur  = conn.cursor()

    # ── Layer 1: ingestion ────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_queue (
            id         SERIAL PRIMARY KEY,
            source     TEXT NOT NULL,
            title      TEXT,
            url        TEXT,
            file_path  TEXT,
            sha256     TEXT UNIQUE,
            status     TEXT DEFAULT 'pending',
            fetched_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # ── Layer 2: processor ───────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id          SERIAL PRIMARY KEY,
            doc_id      INTEGER,
            source      TEXT,
            title       TEXT,
            chunk_index INTEGER,
            chunk_text  TEXT,
            word_count  INTEGER,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS circular_chunks (
            id          SERIAL PRIMARY KEY,
            doc_id      INTEGER,
            parent_id   TEXT,
            source      TEXT,
            title       TEXT,
            domain      TEXT,
            chunk_type  TEXT,
            chunk_index INTEGER,
            chunk_text  TEXT,
            word_count  INTEGER,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS policy_chunks (
            id          SERIAL PRIMARY KEY,
            filename    TEXT,
            parent_id   TEXT,
            domain      TEXT,
            chunk_type  TEXT,
            chunk_index INTEGER,
            chunk_text  TEXT,
            word_count  INTEGER,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks_child (
            id          SERIAL PRIMARY KEY,
            parent_id   INTEGER REFERENCES document_chunks(id) ON DELETE CASCADE,
            child_index INTEGER,
            chunk_text  TEXT,
            word_count  INTEGER,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS policy_chunks_child (
            id          SERIAL PRIMARY KEY,
            parent_id   INTEGER REFERENCES policy_chunks(id) ON DELETE CASCADE,
            child_index INTEGER,
            chunk_text  TEXT,
            word_count  INTEGER,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # ── Layer 4: agents ──────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS compliance_tickets (
            id                SERIAL PRIMARY KEY,
            ticket_id         TEXT UNIQUE,
            circular_id       INTEGER,
            source            TEXT,
            title             TEXT,
            regulator         TEXT,
            domain            TEXT,
            doc_type          TEXT,
            drift_score       FLOAT,
            semantic_score    FLOAT,
            policy_score      FLOAT,
            entity_score      FLOAT,
            priority          TEXT,
            affected_policies TEXT,
            summary           TEXT,
            change_list       TEXT,
            status            TEXT DEFAULT 'open',
            created_at        TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS compliance_audit (
            id          SERIAL PRIMARY KEY,
            ticket_id   TEXT,
            circular_id INTEGER,
            title       TEXT,
            regulator   TEXT,
            domain      TEXT,
            drift_score FLOAT,
            priority    TEXT,
            route       TEXT,
            agent1_out  JSONB,
            agent2_out  JSONB,
            agent3_out  JSONB,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    log.info("All PostgreSQL tables ready.")
