# ============================================================
# src/api.py
# AI Compliance Copilot — FastAPI Backend
#
# What this file does:
# 1. Serves all data to React frontend via REST API
# 2. Reads compliance_tickets and audit from SQLite
# 3. Triggers pipeline on demand
# 4. Handles policy PDF uploads
# 5. Powers the Ask AI chatbot
# ============================================================

import os
import sys
import json
import psycopg2
import psycopg2.extras
import shutil
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from pydantic import BaseModel

# add src to path so we can import our modules
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, "src"))

from db import get_db          # ← shared RDS connection

POLICIES_DIR = os.path.join(BASE_DIR, "data",     "policies")
LOG_PATH     = os.path.join(BASE_DIR, "logs",     "api.log")

# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────

app = FastAPI(
    title       = "AI Compliance Copilot API",
    description = "Backend API for compliance monitoring dashboard",
    version     = "1.0.0"
)

# allow React (port 3000 / 5173) to call FastAPI (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─────────────────────────────────────────
# DB HELPER — uses RDS via db.py
# ─────────────────────────────────────────
# get_db() is imported from db.py above

# ─────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str

class TicketStatusUpdate(BaseModel):
    status: str

# ─────────────────────────────────────────
# ROOT & HEALTH CHECK
# ─────────────────────────────────────────

@app.get("/")
def root_redirect():
    """Redirect root URL to interactive API documentation."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


@app.get("/api/health")
def health_check():
    """Check all system components are running."""
    import requests as req

    status = {
        "api"   : True,
        "sqlite": False,
        "ollama": False,
        "milvus": False,
    }

    # check SQLite
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        status["sqlite"] = True
    except Exception as e:
        log.error("SQLite check failed: %s", e)

    # check Ollama
    try:
        r = req.get("http://localhost:11434/api/tags",
                    timeout=3)
        status["ollama"] = r.status_code == 200
    except Exception:
        status["ollama"] = False

    # check Milvus (GPU server, tunnelled to localhost:19530)
    try:
        from pymilvus import connections, utility
        connections.connect(
            alias="health",
            host=os.getenv("MILVUS_HOST", "127.0.0.1"),
            port=int(os.getenv("MILVUS_PORT", "19530")),
            timeout=3
        )
        cols = utility.list_collections(using="health")
        status["milvus"] = len(cols) > 0
        connections.disconnect("health")
    except Exception as e:
        log.error("Milvus check failed: %s", e)

    return status

# ─────────────────────────────────────────
# STATS — dashboard summary cards
# ─────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    """Return summary statistics for dashboard."""
    conn = get_db()
    c    = conn.cursor()

    # ticket counts
    c.execute("SELECT COUNT(*) FROM compliance_tickets")
    total = list(c.fetchone().values())[0]

    c.execute("""SELECT COUNT(*) FROM compliance_tickets
                 WHERE priority LIKE 'HIGH%'""")
    high = list(c.fetchone().values())[0]

    c.execute("""SELECT COUNT(*) FROM compliance_tickets
                 WHERE priority LIKE 'MEDIUM%'""")
    medium = list(c.fetchone().values())[0]

    c.execute("""SELECT COUNT(*) FROM compliance_tickets
                 WHERE priority LIKE 'LOW%'""")
    low = list(c.fetchone().values())[0]

    c.execute("""SELECT COUNT(*) FROM compliance_audit
                 WHERE route = 'archive'""")
    archived = list(c.fetchone().values())[0]

    c.execute("""SELECT COUNT(*) FROM compliance_tickets
                 WHERE status = 'open'""")
    open_tickets = list(c.fetchone().values())[0]

    c.execute("""SELECT COUNT(*) FROM compliance_tickets
                 WHERE status = 'resolved'""")
    resolved = list(c.fetchone().values())[0]

    # circular counts
    c.execute("SELECT COUNT(*) FROM document_queue")
    total_circulars = list(c.fetchone().values())[0]

    c.execute("""SELECT COUNT(*) FROM document_queue
                 WHERE status = 'processed'""")
    processed_circulars = list(c.fetchone().values())[0]

    # policy counts
    policy_files = set()
    if os.path.exists(POLICIES_DIR):
        policy_files.update([f for f in os.listdir(POLICIES_DIR) if f.endswith(".pdf")])
    c.execute("SELECT DISTINCT filename FROM policy_chunks")
    for r in c.fetchall():
        if list(r.values())[0]:
            policy_files.add(list(r.values())[0])
    total_policies = len(policy_files)

    conn.close()

    return {
        "tickets": {
            "total"   : total,
            "high"    : high,
            "medium"  : medium,
            "low"     : low,
            "archived": archived,
            "open"    : open_tickets,
            "resolved": resolved,
        },
        "circulars": {
            "total"    : total_circulars,
            "processed": processed_circulars,
        },
        "policies": {
            "total": total_policies,
        }
    }

# ─────────────────────────────────────────
# TICKETS
# ─────────────────────────────────────────

@app.get("/api/tickets")
def get_tickets(
    priority  : Optional[str] = None,
    regulator : Optional[str] = None,
    domain    : Optional[str] = None,
    status    : Optional[str] = None,
    limit     : int = 50,
    offset    : int = 0
):
    """Return all compliance tickets with optional filters."""
    conn = get_db()
    c    = conn.cursor()

    query  = "SELECT * FROM compliance_tickets WHERE 1=1"
    params = []

    if priority:
        query += " AND priority LIKE %s"
        params.append(f"%{priority}%")
    if regulator:
        query += " AND regulator = %s"
        params.append(regulator)
    if domain:
        query += " AND domain = %s"
        params.append(domain)
    if status:
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    tickets = []
    for row in rows:
        t = dict(row)
        try:
            t["affected_policies"] = json.loads(
                t.get("affected_policies") or "[]"
            )
        except Exception:
            t["affected_policies"] = []
        tickets.append(t)

    return {"tickets": tickets, "total": len(tickets)}


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    """Return single ticket detail."""
    conn = get_db()
    c    = conn.cursor()

    c.execute("""SELECT * FROM compliance_tickets
                 WHERE ticket_id = %s""", (ticket_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404,
                            detail="Ticket not found")

    t = dict(row)
    try:
        t["affected_policies"] = json.loads(
            t.get("affected_policies") or "[]"
        )
    except Exception:
        t["affected_policies"] = []

    return t


@app.patch("/api/tickets/{ticket_id}/status")
def update_ticket_status(ticket_id: str,
                         body: TicketStatusUpdate):
    """Update ticket status — open / resolved / in_review / in_progress / archived."""
    allowed = ["open", "resolved", "in_review", "in_progress", "archived"]
    if body.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of {allowed}"
        )

    conn = get_db()
    c    = conn.cursor()
    c.execute("""UPDATE compliance_tickets
                 SET status = %s
                 WHERE ticket_id = %s""",
              (body.status, ticket_id))
    conn.commit()
    conn.close()

    return {"ticket_id": ticket_id,
            "status"   : body.status,
            "updated"  : True}


@app.get("/api/tickets/export/csv")
def export_tickets_csv():
    """Export all compliance tickets as downloadable CSV file."""
    import io, csv
    from fastapi.responses import StreamingResponse

    conn = get_db()
    c    = conn.cursor()
    c.execute("""
        SELECT ticket_id, title, regulator, domain, doc_type,
               drift_score, priority, status, created_at
        FROM compliance_tickets
        ORDER BY created_at DESC
    """)
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ticket ID", "Title", "Regulator", "Domain", "Doc Type", "Drift Score", "Priority", "Status", "Created At"])
    for r in rows:
        writer.writerow([
            r["ticket_id"],
            r["title"],
            r["regulator"],
            r["domain"],
            r["doc_type"],
            r["drift_score"],
            r["priority"],
            r["status"],
            r["created_at"]
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=compliance_tickets_report.csv"}
    )

# ─────────────────────────────────────────
# AUDIT TRAIL
# ─────────────────────────────────────────

@app.get("/api/audit")
def get_audit(limit: int = 100, offset: int = 0):
    """Return full audit trail."""
    conn = get_db()
    c    = conn.cursor()

    c.execute("""SELECT * FROM compliance_audit
                 ORDER BY created_at DESC
                 LIMIT %s OFFSET %s""",
              (limit, offset))
    rows = c.fetchall()
    conn.close()

    audit = []
    for row in rows:
        a = dict(row)
        for field in ["agent1_out", "agent2_out",
                      "agent3_out"]:
            try:
                a[field] = json.loads(a.get(field) or "{}")
            except Exception:
                a[field] = {}
        audit.append(a)

    return {"audit": audit, "total": len(audit)}

# ─────────────────────────────────────────
# DRIFT SCORES — for chart
# ─────────────────────────────────────────

@app.get("/api/drift-scores")
def get_drift_scores():
    """Return drift scores for all tickets — for chart."""
    conn = get_db()
    c    = conn.cursor()

    c.execute("""
        SELECT ticket_id, title, regulator, domain,
               drift_score, semantic_score,
               policy_score, entity_score,
               priority, created_at
        FROM compliance_tickets
        ORDER BY created_at DESC
    """)
    rows = c.fetchall()
    conn.close()

    return {"scores": [dict(r) for r in rows]}


@app.get("/api/dashboard-summary")
def get_dashboard_summary():
    """Return domain/regulator breakdowns and recent activity for dashboard."""
    conn = get_db()
    c    = conn.cursor()

    c.execute("""
        SELECT domain, COUNT(*) as count
        FROM compliance_tickets
        GROUP BY domain
        ORDER BY count DESC
    """)
    by_domain = [dict(r) for r in c.fetchall()]

    c.execute("""
        SELECT regulator, COUNT(*) as count
        FROM compliance_tickets
        GROUP BY regulator
        ORDER BY count DESC
    """)
    by_regulator = [dict(r) for r in c.fetchall()]

    c.execute("""
        SELECT ticket_id, title, regulator, domain, priority, created_at
        FROM compliance_tickets
        ORDER BY created_at DESC
        LIMIT 5
    """)
    recent_tickets = [dict(r) for r in c.fetchall()]

    conn.close()

    return {
        "by_domain": by_domain,
        "by_regulator": by_regulator,
        "recent_tickets": recent_tickets
    }


# ─────────────────────────────────────────
# PIPELINE — trigger manually from UI
# ─────────────────────────────────────────

def run_full_pipeline_task():
    """Background execution function for full compliance pipeline."""
    try:
        log.info("Pipeline background task starting...")
        from ingestion import init_db, fetch_sebi, fetch_sebi_historical
        init_db()
        fetch_sebi()
        fetch_sebi_historical()

        from processor import init_chunks_table, init_policy_chunks_table, process_pending
        init_chunks_table()
        init_policy_chunks_table()
        process_pending()

        from embeddings import embed_circulars, embed_policies
        embed_circulars()
        embed_policies()

        from agents import run_pipeline
        run_pipeline()
        log.info("Pipeline background task completed successfully.")
    except Exception as e:
        log.error("Pipeline background execution error: %s", e)


@app.post("/api/pipeline/run")
def run_pipeline_endpoint(background_tasks: BackgroundTasks):
    """Trigger full pipeline asynchronously in background to prevent HTTP timeout Network Errors."""
    log.info("Pipeline execution requested from UI")
    background_tasks.add_task(run_full_pipeline_task)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as count FROM compliance_tickets")
    row = c.fetchone()
    total = row['count'] if row else 0
    conn.close()

    return {
        "status" : "success",
        "message": "Pipeline execution started in background! Ingestion, PaddleOCR, Milvus embeddings, and Multi-Agent audit are processing.",
        "total_tickets": total
    }

# ─────────────────────────────────────────
# CHATBOT — Ask AI
# ─────────────────────────────────────────

@app.post("/api/chat")
def chat(body: ChatRequest):
    """RAG-powered chatbot endpoint — searches both bank policies
    and SEBI circulars for content questions, and reads the live
    ticket database for stats/count/priority questions."""
    try:
        from embeddings import search_similar, COL_POLICIES, COL_CIRCULARS
        from groq import Groq

        GROQ_API_KEY = os.getenv("GROQ_API_KEY", "gsk_YOUR_GROQ_API_KEY_HERE")

        clean_query = body.query.strip().strip('"').strip("'")
        query_lower = clean_query.lower()

        # ── detect if this is a question about ticket data
        # (counts, priorities, status) rather than document content ──
        STATS_KEYWORDS = [
            "how many", "count", "total ticket", "total number",
            "highest priority", "highest drift", "lowest priority",
            "which ticket", "list ticket", "list all ticket",
            "open ticket", "resolved ticket", "archived ticket",
            "ticket status", "ticket count", "raised overall",
            "how much ticket", "priority ticket", "top ticket",
            "ticket", "tickets", "system"
        ]
        is_stats_question = any(kw in query_lower for kw in STATS_KEYWORDS)

        stats_context = ""
        if is_stats_question:
            conn = get_db()
            c    = conn.cursor()
            c.execute("""
                SELECT ticket_id, title, regulator, domain,
                       drift_score, priority, status
                FROM compliance_tickets
                ORDER BY drift_score DESC
            """)
            rows = c.fetchall()
            conn.close()

            lines = [
                f"- {r['ticket_id']} | {r['title'][:80]} | "
                f"regulator={r['regulator']} | domain={r['domain']} | "
                f"drift_score={r['drift_score']} | priority={r['priority']} | "
                f"status={r['status']}"
                for r in rows
            ]
            stats_context = (
                f"TICKET DATABASE — {len(rows)} total tickets currently raised in the system, "
                f"sorted highest drift score first:\n" + "\n".join(lines)
            )

        # ── document search — always run, useful for most questions ──
        policy_chunks = search_similar(
            query_text      = clean_query,
            n_results       = 3,
            collection_name = COL_POLICIES
        )
        circular_chunks = search_similar(
            query_text      = clean_query,
            n_results       = 3,
            collection_name = COL_CIRCULARS
        )
        chunks = policy_chunks + circular_chunks

        # If vector search produced low similarity (< 0.20), fallback to direct PostgreSQL text search on policy_chunks
        max_sim = max([c.get("similarity", 0) for c in chunks], default=0)
        if max_sim < 0.20:
            try:
                conn = get_db()
                c = conn.cursor()
                stopwords = {"what", "is", "the", "for", "and", "under", "our", "bank", "policy", "guidelines", "procedure", "how", "many", "does"}
                keywords = [w for w in clean_query.lower().split() if len(w) > 2 and w not in stopwords]
                if keywords:
                    like_clauses = " OR ".join(["LOWER(chunk_text) LIKE %s"] * len(keywords))
                    params = tuple(f"%{kw}%" for kw in keywords)
                    c.execute(f"""
                        SELECT filename, chunk_text
                        FROM policy_chunks
                        WHERE {like_clauses}
                        LIMIT 3
                    """, params)
                    db_rows = c.fetchall()
                    for r in db_rows:
                        chunks.append({
                            "metadata": {"filename": r['filename']},
                            "text": r['chunk_text'],
                            "similarity": 0.85
                        })
                conn.close()
            except Exception as ex:
                log.warning("PostgreSQL text search fallback failed: %s", ex)

        doc_context = "\n\n".join([
            f"Source: {c['metadata'].get('filename', c['metadata'].get('title','unknown'))}"
            f"\n{c['text'][:1500]}"
            for c in chunks
        ])

        combined_context = ""
        if stats_context:
            combined_context += stats_context + "\n\n"
        if doc_context:
            combined_context += f"DOCUMENT EXCERPTS:\n{doc_context}"

        prompt = f"""You are the official AI Compliance Copilot for Bank of India's Compliance Team.

GROUNDING & RESPONSE INSTRUCTIONS:
1. You may respond politely to basic greetings (e.g., "Hello", "Good morning").
2. For questions regarding tickets, counts, policies, circulars, or compliance guidelines:
   - Answer using the TICKET DATABASE or DOCUMENT EXCERPTS provided below.
   - Synthesize the facts clearly and cite the exact source document or ticket details.
3. If neither the TICKET DATABASE nor DOCUMENT EXCERPTS contain relevant information to answer the question, state:
   "I do not have information about this in the internal bank policies, regulatory circulars, or compliance database currently available."

{combined_context if combined_context else "(No relevant internal documents or ticket records retrieved)"}

User Question: {clean_query}

Answer:"""

        try:
            client   = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model       = "qwen-2.5-coder-32b",
                messages    = [{"role": "user", "content": prompt}],
                temperature = 0.3,
                max_tokens  = 512,
            )
            answer = response.choices[0].message.content.strip()
        except Exception as groq_err:
            log.warning("Groq API unavailable in chat_endpoint (%s). Synthesizing answer from context...", groq_err)
            if stats_context:
                answer = f"Based on the compliance database:\n\n{stats_context[:1000]}"
            elif chunks:
                answer = f"Based on the internal bank policies:\n\n{chunks[0]['text'][:800]}"
            else:
                answer = "I do not have information about this in the internal bank policies, regulatory circulars, or compliance database currently available."

        sources = [
            {
                "filename"  : c["metadata"].get("filename") or c["metadata"].get("title") or "unknown",
                "similarity": c["similarity"],
                "text"      : c["text"][:200]
            }
            for c in chunks
        ]

        return {"answer": answer, "sources": sources}

    except Exception as e:
        log.error("Chat failed: %s", e)
        return {"answer": f"Unable to process query: {str(e)}", "sources": []}

# ─────────────────────────────────────────
# POLICIES — list and upload
# ─────────────────────────────────────────

@app.get("/api/policies")
def get_policies():
    """Return list of all policy documents with chunk counts and S3 URLs."""
    conn = get_db()
    c    = conn.cursor()

    c.execute("""
        SELECT filename,
               COUNT(*) as chunks,
               MAX(created_at) as last_updated
        FROM policy_chunks
        GROUP BY filename
        ORDER BY filename
    """)
    rows = c.fetchall()
    conn.close()

    db_map = {row["filename"]: row for row in rows}

    all_files = set(db_map.keys())
    if os.path.exists(POLICIES_DIR):
        for f in os.listdir(POLICIES_DIR):
            if f.endswith(".pdf"):
                all_files.add(f)

    policies = []
    for fname in sorted(all_files):
        row = db_map.get(fname)
        chunks = row["chunks"] if row else 0
        last_updated = row["last_updated"] if row else datetime.now().isoformat()
        policies.append({
            "filename"    : fname,
            "chunks"      : chunks,
            "last_updated": last_updated,
            "s3_url"      : f"https://compliance-frontend-sujal-2026.s3.ap-south-1.amazonaws.com/policies/{fname}"
        })

    return {"policies": policies}


def _reembed_policy_task(filename: str, child_chunks: list):
    """Background task to re-embed policy child chunks into Milvus using BATCH execution."""
    if not child_chunks:
        return
    try:
        from embeddings import get_collection, get_embeddings_batch, detect_domain, COL_POLICIES
        collection = get_collection(COL_POLICIES)

        existing = collection.query(
            expr          = f'filename == "{filename}"',
            output_fields = ["id"]
        )
        if existing:
            id_expr = ", ".join([f'"{r["id"]}"' for r in existing])
            collection.delete(expr=f"id in [{id_expr}]")
            collection.flush()
            log.info("Deleted %d old vectors for %s", len(existing), filename)

        texts = [row['chunk_text'] for row in child_chunks]
        vectors = get_embeddings_batch(texts)

        records = []
        for i, row in enumerate(child_chunks):
            if i < len(vectors) and vectors[i]:
                milvus_id = f"policy_{row['parent_id']}_{row['child_index']}"
                records.append({
                    "id"         : milvus_id,
                    "vector"     : vectors[i],
                    "document"   : row['chunk_text'][:65535],
                    "doc_id"     : "",
                    "parent_id"  : str(row['parent_id']),
                    "source"     : "",
                    "title"      : "",
                    "child_index": str(row['child_index']),
                    "domain"     : detect_domain(row['chunk_text']),
                    "filename"   : filename,
                })

        if records:
            collection.insert(records)
            collection.flush()
            log.info("Background policy embedding complete for %s: %d chunks embedded.", filename, len(records))
    except Exception as milvus_err:
        log.warning("Background Milvus vector indexing notice for %s (%s).", filename, milvus_err)


def _process_and_embed_policy_bg(filename: str, save_path: str, pdf_bytes: bytes, s3_url: str):
    """Background task to run S3 upload, OCR text extraction, chunking, RDS save, and Milvus embedding."""
    try:
        try:
            from s3_utils import upload_bytes_to_s3
            s3_key = f"policies/{filename}"
            upload_bytes_to_s3(pdf_bytes, s3_key)
            log.info("Policy uploaded to S3: %s", s3_url)
        except Exception as s3_err:
            log.warning("S3 upload warning (%s). Local copy saved.", s3_err)

        from processor import extract_pdf_text, clean_text, chunk_text_parent_child, save_policy_chunks
        text    = extract_pdf_text(save_path)
        cleaned = clean_text(text)
        chunks  = chunk_text_parent_child(cleaned)

        conn = get_db()
        c    = conn.cursor()
        c.execute("DELETE FROM policy_chunks WHERE filename=%s", (filename,))
        conn.commit()
        conn.close()

        save_policy_chunks(filename, chunks)

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM policy_chunks WHERE filename=%s", (filename,))
        parent_rows = c.fetchall()
        parent_ids = [r['id'] for r in parent_rows]

        child_chunks = []
        if parent_ids:
            placeholders = ", ".join(["%s"] * len(parent_ids))
            c.execute(f"""
                SELECT id, parent_id, child_index, chunk_text
                FROM policy_chunks_child
                WHERE parent_id IN ({placeholders})
            """, tuple(parent_ids))
            child_chunks = [dict(r) for r in c.fetchall()]
        conn.close()

        _reembed_policy_task(filename, child_chunks)
        log.info("Complete background policy processing finished for %s!", filename)
    except Exception as bg_err:
        log.error("Background policy processing error for %s: %s", filename, bg_err)


@app.post("/api/policies/upload")
async def upload_policy(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a new or updated bank policy PDF directly (0.2s Instant Response)."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted"
        )

    try:
        pdf_bytes = await file.read()

        os.makedirs(POLICIES_DIR, exist_ok=True)
        save_path = os.path.join(POLICIES_DIR, file.filename)
        with open(save_path, "wb") as f:
            f.write(pdf_bytes)

        s3_url = f"https://compliance-frontend-sujal-2026.s3.ap-south-1.amazonaws.com/policies/{file.filename}"

        # Offload all OCR, text extraction, S3, RDS, and Milvus to BackgroundTasks
        background_tasks.add_task(_process_and_embed_policy_bg, file.filename, save_path, pdf_bytes, s3_url)

        return {
            "status"  : "success",
            "filename": file.filename,
            "s3_url"  : s3_url,
            "message" : f"Policy '{file.filename}' uploaded successfully. Processing and vector indexing running in background."
        }

    except Exception as e:
        log.error("Policy upload failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
        raise HTTPException(status_code=500,
                            detail=str(e))


@app.get("/api/policies/{filename}/chunks")
def get_policy_chunks(filename: str):
    """Return all text chunks for a single policy document."""
    conn = get_db()
    c    = conn.cursor()

    c.execute("""
        SELECT chunk_index, chunk_text, word_count
        FROM policy_chunks
        WHERE filename = %s
        ORDER BY chunk_index
    """, (filename,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404,
                            detail="Policy not found")

    return {
        "filename": filename,
        "chunks"  : [dict(r) for r in rows]
    }


@app.get("/api/policies/{filename}/file")
def get_policy_file(filename: str):
    """Serve the raw policy PDF file directly from S3 or local fallback."""
    from fastapi.responses import RedirectResponse

    s3_url = f"https://compliance-frontend-sujal-2026.s3.ap-south-1.amazonaws.com/policies/{filename}"
    file_path = os.path.join(POLICIES_DIR, filename)

    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'}
        )

    return RedirectResponse(s3_url)


@app.get("/api/circulars")
def get_circulars():
    """Return all ingested circulars with their processing outcome —
    whether they became a ticket, got archived, or are still pending."""
    conn = get_db()
    c    = conn.cursor()

    c.execute("""
        SELECT
            dq.id,
            dq.source,
            dq.title,
            dq.url,
            dq.status,
            dq.fetched_at,
            ca.route          AS outcome,
            ca.drift_score,
            ct.ticket_id
        FROM document_queue dq
        LEFT JOIN compliance_audit ca ON ca.circular_id = dq.id
        LEFT JOIN compliance_tickets ct ON ct.circular_id = dq.id
        ORDER BY dq.id DESC
    """)
    rows = c.fetchall()
    conn.close()

    return {
        "circulars": [dict(r) for r in rows],
        "total": len(rows)
    }



@app.get("/api/circulars/{circular_id}/file")
def get_circular_file(circular_id: int):
    """Serve the raw circular PDF or TXT document for inline viewing in browser."""
    from fastapi.responses import RedirectResponse
    conn = get_db()
    c    = conn.cursor()
    c.execute("SELECT source, file_path FROM document_queue WHERE id = %s",
              (circular_id,))
    row = c.fetchone()
    conn.close()

    if not row or not row["file_path"]:
        raise HTTPException(status_code=404,
                            detail="Circular document not available")

    file_path = row["file_path"]
    source = row.get("source") or "sebi"

    # Redirect directly to S3 if file_path is already an S3 URL
    if file_path and (file_path.startswith("http://") or file_path.startswith("https://")):
        return RedirectResponse(file_path)

    # Local file exists check
    if os.path.exists(file_path):
        media_type = "text/plain; charset=utf-8" if file_path.lower().endswith(".txt") else "application/pdf"
        filename = os.path.basename(file_path)
        return FileResponse(
            file_path,
            media_type=media_type,
            headers={"Content-Disposition": f'inline; filename="{filename}"'}
        )

    # S3 redirect fallback
    clean_filename = file_path.replace("\\", "/").split("/")[-1]
    s3_key = f"circulars/{source}_{clean_filename}"
    s3_url = f"https://compliance-frontend-sujal-2026.s3.ap-south-1.amazonaws.com/{s3_key}"

    return RedirectResponse(s3_url)



# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app",
                host    = "0.0.0.0",
                port    = 8000,
                reload  = True)
