# ============================================================
# src/embeddings.py
# AI Compliance Copilot — Layer 3: RAG Infrastructure
# Member 3 — ML + Embeddings Engineer
#
# What this file does:
# 1. Embeds circular CHILD chunks (any regulator) → Milvus collection 1
# 2. Embeds bank policy CHILD chunks → Milvus collection 2
#    (children are embedded for precise search; each vector's
#    metadata carries parent_id so the matched PARENT's full text
#    can be returned as broader context to the LLM)
# 3. Provides search_similar()  → used by Agent 2
# 4. Provides calculate_drift() → used by Agent 2
#
# Vector DB: Milvus (GPU server at 192.168.6.50 via SSH tunnel)
# Embedding: bge-m3 via Ollama (1024-dim, COSINE metric)
#
# No agents here. No LLM here. Pure tools.
# ============================================================

import os
import sys
import logging
import requests
import numpy as np

# ── path fix so 'from db import get_db' works when called from api.py ──
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from db import get_db

from pymilvus import (
    connections, utility,
    FieldSchema, CollectionSchema, DataType,
    Collection
)

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH     = os.path.join(BASE_DIR, "db",   "compliance.db")
LOG_PATH    = os.path.join(BASE_DIR, "logs", "embeddings.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

OLLAMA_URL   = "http://localhost:11434"
EMBED_MODEL  = "bge-m3"
EMBED_DIM    = 1024          # bge-m3 output dimension

# ── Batch embedding config ──────────────────────────────
# Number of texts sent in ONE /api/embed HTTP call to Ollama.
# 1 round-trip through SSH tunnel = vectors for EMBED_BATCH texts.
# Increase for more speed; decrease to 4 if you see OOM errors on GPU.
EMBED_BATCH    = 8
# Number of vectors to batch-insert into Milvus at once.
INSERT_BATCH_SIZE = 50

# Milvus connection (127.0.0.1 = SSH-tunnelled GPU server)
MILVUS_HOST = os.getenv("MILVUS_HOST", "127.0.0.1")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))

# Milvus collection names (same logical names as before)
COL_CIRCULARS = "sebi_circulars"
COL_POLICIES  = "bank_policies"

# Domain keywords for Agent 1 classification
DOMAIN_KEYWORDS = {
    "Investment Advisory" : [
        "investment adviser", "nism", "paia", "ia regulations",
        "portfolio", "advisory", "wealth management"
    ],
    "KYC / AML" : [
        "kyc", "know your customer", "aml", "anti money laundering",
        "cft", "customer acceptance", "due diligence"
    ],
    "Capital Adequacy" : [
        "capital adequacy", "crar", "tier 1", "tier 2",
        "risk weighted", "basel", "prudential norms"
    ],
    "Consumer Protection" : [
        "advertisement", "grievance", "redressal", "complaint",
        "customer protection", "investor protection", "disclosure"
    ],
    "Mutual Funds" : [
        "mutual fund", "amc", "nfo", "nav", "scheme",
        "categorization", "aif", "portfolio manager"
    ],
    "Deposit / Lending" : [
        "deposit", "loan", "lending", "borrower", "credit",
        "interest rate", "npa", "provisioning"
    ],
    "Market Infrastructure" : [
        "stock exchange", "clearing corporation", "settlement",
        "derivatives", "commodity", "etf", "price band"
    ],
    "Reporting / Compliance" : [
        "reporting", "disclosure", "returns", "filing",
        "compliance", "regulatory reporting", "audit"
    ]
}

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
# MILVUS CONNECTION
# ─────────────────────────────────────────

def get_milvus_client():
    """Connect to Milvus if not already connected, with Milvus Lite fallback."""
    if not connections.has_connection("default"):
        try:
            connections.connect(
                alias   = "default",
                host    = MILVUS_HOST,
                port    = MILVUS_PORT,
                timeout = 3
            )
            log.info("Connected to Milvus server at %s:%s", MILVUS_HOST, MILVUS_PORT)
            return
        except Exception as e:
            log.warning("Primary Milvus server unreachable (%s). Trying Milvus Lite URI...", e)

        # Fallback to Milvus Lite local file database
        try:
            milvus_db = os.path.join(BASE_DIR, "db", "milvus_compliance.db")
            os.makedirs(os.path.dirname(milvus_db), exist_ok=True)
            connections.connect(
                alias = "default",
                uri   = milvus_db
            )
            log.info("Connected to Milvus Lite at %s", milvus_db)
        except Exception as e2:
            log.error("Milvus connect error: %s", e2)
            raise e2


def _make_schema() -> CollectionSchema:
    """Unified Milvus schema for both circular and policy collections.
    Unused fields (e.g. filename for circulars) are stored as empty strings."""
    fields = [
        FieldSchema(name="id",          dtype=DataType.VARCHAR,      is_primary=True, max_length=256),
        FieldSchema(name="vector",      dtype=DataType.FLOAT_VECTOR, dim=EMBED_DIM),
        FieldSchema(name="document",    dtype=DataType.VARCHAR,      max_length=65535),
        FieldSchema(name="doc_id",      dtype=DataType.VARCHAR,      max_length=64),
        FieldSchema(name="parent_id",   dtype=DataType.VARCHAR,      max_length=64),
        FieldSchema(name="source",      dtype=DataType.VARCHAR,      max_length=64),
        FieldSchema(name="title",       dtype=DataType.VARCHAR,      max_length=256),
        FieldSchema(name="child_index", dtype=DataType.VARCHAR,      max_length=16),
        FieldSchema(name="domain",      dtype=DataType.VARCHAR,      max_length=128),
        FieldSchema(name="filename",    dtype=DataType.VARCHAR,      max_length=256),
    ]
    return CollectionSchema(fields=fields,
                            description="Compliance vector collection",
                            enable_dynamic_field=False)


def get_collection(name: str) -> Collection:
    """Get or create a Milvus collection with HNSW/COSINE index, then load it."""
    get_milvus_client()

    if utility.has_collection(name):
        col = Collection(name)
        col.load()
        return col

    # Create collection with unified schema
    col = Collection(name=name, schema=_make_schema())
    log.info("Created Milvus collection: %s", name)

    # Build GPU-accelerated HNSW index with cosine metric (fallback to FLAT/AUTOINDEX for Milvus Lite)
    index_params = {
        "metric_type": "COSINE",
        "index_type" : "HNSW",
        "params"     : {"M": 16, "efConstruction": 200}
    }
    try:
        col.create_index(field_name="vector", index_params=index_params)
        log.info("Built HNSW/COSINE index on collection: %s", name)
    except Exception as e:
        log.warning("HNSW index creation failed (%s), falling back to FLAT/AUTOINDEX for Milvus Lite compatibility...", e)
        fallback_params = {"metric_type": "COSINE", "index_type": "FLAT", "params": {}}
        col.create_index(field_name="vector", index_params=fallback_params)
        log.info("Built FLAT/COSINE index on collection: %s", name)

    col.load()
    return col

# ─────────────────────────────────────────
# EMBEDDING GENERATION (Ollama + FastEmbed Fallback)
# ─────────────────────────────────────────

_fastembed_model = None

def _get_fastembed_model():
    global _fastembed_model
    if _fastembed_model is None:
        try:
            from fastembed import TextEmbedding
            log.info("Loading local FastEmbed model (BAAI/bge-small-en-v1.5)...")
            _fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            log.info("FastEmbed model loaded successfully.")
        except Exception as e:
            log.error("Failed to load FastEmbed model: %s", e)
    return _fastembed_model


def get_embedding(text: str) -> list:
    """Convert a single text to vector using Ollama or FastEmbed fallback (1024-dim)."""
    vector = None
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text[:8000]},
            timeout=5
        )
        if r.status_code == 200:
            vector = r.json()["embedding"]
    except Exception:
        pass

    # FastEmbed local fallback
    if vector is None:
        try:
            model = _get_fastembed_model()
            if model:
                embeddings = list(model.embed([text[:8000]]))
                vector = embeddings[0].tolist()
        except Exception as e:
            log.error("FastEmbed embedding failed: %s", e)

    # Ensure vector matches Milvus collection schema (1024 dimensions)
    if vector:
        if len(vector) < 1024:
            vector = vector + [0.0] * (1024 - len(vector))
        elif len(vector) > 1024:
            vector = vector[:1024]

    return vector


def get_embeddings_batch(texts: list) -> list:
    """
    Convert a LIST of texts to vectors.
    Tries Ollama batch endpoint first, falls back to FastEmbed locally.
    """
    if not texts:
        return []

    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": [t[:8000] for t in texts]},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if "embeddings" in data:
                return data["embeddings"]
            if "embedding" in data:
                return [data["embedding"]]
    except Exception as e:
        log.warning("Ollama batch embed unavailable (%s). Using FastEmbed fallback.", e)

    # FastEmbed local fallback
    try:
        model = _get_fastembed_model()
        if model:
            embeddings = list(model.embed([t[:8000] for t in texts]))
            res = []
            for e in embeddings:
                vec = e.tolist()
                if len(vec) < 1024:
                    vec = vec + [0.0] * (1024 - len(vec))
                elif len(vec) > 1024:
                    vec = vec[:1024]
                res.append(vec)
            return res
    except Exception as e:
        log.error("FastEmbed batch embedding failed: %s", e)

    return [None] * len(texts)


def check_ollama() -> bool:
    """Check if Ollama or FastEmbed is ready."""
    try:
        r      = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        if any(EMBED_MODEL in m for m in models):
            log.info("Ollama ready. Model: %s", EMBED_MODEL)
            return True
    except Exception:
        pass

    # If Ollama is down, check FastEmbed
    model = _get_fastembed_model()
    if model:
        log.info("FastEmbed fallback ready (BAAI/bge-m3).")
        return True

    return False

def check_milvus() -> bool:
    """Check if Milvus GPU server is reachable."""
    try:
        get_milvus_client()
        cols = utility.list_collections()
        log.info("Milvus ready. Collections: %s", cols)
        return True
    except Exception as e:
        log.error("Milvus not reachable at %s:%d — %s", MILVUS_HOST, MILVUS_PORT, e)
        log.error("Ensure SSH tunnel is open: "
                  "ssh -N -L 19530:localhost:19530 student15@192.168.6.50 -p 22")
        return False

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def _get_existing_ids(col: Collection) -> set:
    """Return set of all IDs already stored in a Milvus collection."""
    if col.num_entities == 0:
        return set()
    # Query all IDs (paginated in chunks of 16384 — Milvus default limit)
    existing = set()
    offset   = 0
    batch    = 16384
    while True:
        rows = col.query(
            expr         = "id != ''",
            output_fields= ["id"],
            limit        = batch,
            offset       = offset
        )
        if not rows:
            break
        existing.update(r["id"] for r in rows)
        if len(rows) < batch:
            break
        offset += batch
    return existing


def _build_id_expr(ids: list) -> str:
    """Build a Milvus expr string for id in [list]."""
    escaped = ", ".join([f'"{i}"' for i in ids])
    return f"id in [{escaped}]"

# ─────────────────────────────────────────
# EMBED CIRCULARS (CHILD-LEVEL)
# ─────────────────────────────────────────

def embed_circulars():
    """Embed all circular CHILD chunks (any regulator) into Milvus.
    Uses true batch embedding via /api/embed — 1 SSH round-trip per EMBED_BATCH texts."""
    log.info("=" * 50)
    log.info("Embedding circulars — batch_size:%d  insert_batch:%d",
             EMBED_BATCH, INSERT_BATCH_SIZE)

    conn = get_db()
    c    = conn.cursor()
    c.execute("""
        SELECT dcc.id, dcc.parent_id, dcc.child_index, dcc.chunk_text,
               dc.doc_id, dc.source, dc.title
        FROM document_chunks_child dcc
        JOIN document_chunks dc ON dcc.parent_id = dc.id
    """)
    chunks = c.fetchall()
    conn.close()

    log.info("Found %d circular child chunks to embed", len(chunks))

    col          = get_collection(COL_CIRCULARS)
    existing_ids = _get_existing_ids(col)
    embedded = skipped = failed = 0

    # ── Build work queue (skip already-embedded chunks) ────────────
    work_items = []
    for row in chunks:
        child_id = row['id']
        parent_id = row['parent_id']
        child_index = row['child_index']
        chunk_text = row['chunk_text']
        doc_id = row['doc_id']
        source = row['source']
        title = row['title']

        milvus_id = f"{source}_{parent_id}_{child_index}"
        if milvus_id in existing_ids:
            skipped += 1
            continue
        row_data = {
            "id"         : milvus_id,
            "document"   : chunk_text[:65535],
            "doc_id"     : str(doc_id),
            "parent_id"  : str(parent_id),
            "source"     : source or "",
            "title"      : (title or "")[:256],
            "child_index": str(child_index),
            "domain"     : detect_domain(chunk_text),
            "filename"   : ""
        }
        work_items.append((milvus_id, row_data, chunk_text))

    log.info("Skipped %d already-embedded. Embedding %d new chunks with batch_size=%d...",
             skipped, len(work_items), EMBED_BATCH)

    # ── True batch embedding: EMBED_BATCH texts per SSH round-trip ──
    insert_buf = []
    for i in range(0, len(work_items), EMBED_BATCH):
        batch_items  = work_items[i : i + EMBED_BATCH]
        batch_texts  = [item[2] for item in batch_items]   # chunk_text
        batch_ids    = [item[0] for item in batch_items]   # milvus_id
        batch_rows   = [item[1] for item in batch_items]   # row_data dict

        vectors = get_embeddings_batch(batch_texts)

        for milvus_id, vector, row_data in zip(batch_ids, vectors, batch_rows):
            if not vector:
                log.warning("Embedding failed for: %s", milvus_id)
                failed += 1
                continue
            row_data["vector"] = vector
            insert_buf.append(row_data)

        # Flush insert buffer every INSERT_BATCH_SIZE records
        if len(insert_buf) >= INSERT_BATCH_SIZE:
            col.insert(insert_buf)
            embedded += len(insert_buf)
            log.info("Progress: %d / %d embedded", embedded, len(work_items))
            insert_buf = []

    # Insert remaining
    if insert_buf:
        col.insert(insert_buf)
        embedded += len(insert_buf)
        log.info("Final insert: %d vectors", len(insert_buf))

    col.flush()
    log.info("Circulars → embedded:%d  skipped:%d  failed:%d  total_in_db:%d",
             embedded, skipped, failed, col.num_entities)

# ─────────────────────────────────────────
# EMBED BANK POLICIES (CHILD-LEVEL)
# ─────────────────────────────────────────

def embed_policies():
    """Embed all policy CHILD chunks into Milvus.
    Uses true batch embedding via /api/embed — 1 SSH round-trip per EMBED_BATCH texts."""
    log.info("=" * 50)
    log.info("Embedding policies — batch_size:%d  insert_batch:%d",
             EMBED_BATCH, INSERT_BATCH_SIZE)

    conn = get_db()
    c    = conn.cursor()
    c.execute("""
        SELECT pcc.id, pcc.parent_id, pcc.child_index, pcc.chunk_text,
               pc.filename
        FROM policy_chunks_child pcc
        JOIN policy_chunks pc ON pcc.parent_id = pc.id
    """)
    chunks = c.fetchall()
    conn.close()

    log.info("Found %d policy child chunks to embed", len(chunks))

    col          = get_collection(COL_POLICIES)
    existing_ids = _get_existing_ids(col)
    embedded = skipped = failed = 0

    # ── Build work queue (skip already-embedded chunks) ────────────
    work_items = []
    for row in chunks:
        child_id = row['id']
        parent_id = row['parent_id']
        child_index = row['child_index']
        chunk_text = row['chunk_text']
        filename = row['filename']

        milvus_id = f"policy_{parent_id}_{child_index}"
        if milvus_id in existing_ids:
            skipped += 1
            continue
        row_data = {
            "id"         : milvus_id,
            "document"   : chunk_text[:65535],
            "doc_id"     : "",
            "parent_id"  : str(parent_id),
            "source"     : "",
            "title"      : "",
            "child_index": str(child_index),
            "domain"     : detect_domain(chunk_text),
            "filename"   : filename or ""
        }
        work_items.append((milvus_id, row_data, chunk_text))

    log.info("Skipped %d already-embedded. Embedding %d new chunks with batch_size=%d...",
             skipped, len(work_items), EMBED_BATCH)

    # ── True batch embedding: EMBED_BATCH texts per SSH round-trip ──
    insert_buf = []
    for i in range(0, len(work_items), EMBED_BATCH):
        batch_items  = work_items[i : i + EMBED_BATCH]
        batch_texts  = [item[2] for item in batch_items]
        batch_ids    = [item[0] for item in batch_items]
        batch_rows   = [item[1] for item in batch_items]

        vectors = get_embeddings_batch(batch_texts)

        for milvus_id, vector, row_data in zip(batch_ids, vectors, batch_rows):
            if not vector:
                log.warning("Embedding failed for: %s", milvus_id)
                failed += 1
                continue
            row_data["vector"] = vector
            insert_buf.append(row_data)

        # Flush insert buffer every INSERT_BATCH_SIZE records
        if len(insert_buf) >= INSERT_BATCH_SIZE:
            col.insert(insert_buf)
            embedded += len(insert_buf)
            log.info("Progress: %d / %d embedded", embedded, len(work_items))
            insert_buf = []

    # Insert remaining
    if insert_buf:
        col.insert(insert_buf)
        embedded += len(insert_buf)
        log.info("Final insert: %d vectors", len(insert_buf))

    col.flush()
    log.info("Policies → embedded:%d  skipped:%d  failed:%d  total_in_db:%d",
             embedded, skipped, failed, col.num_entities)

# ─────────────────────────────────────────
# DOMAIN DETECTION
# Used by Agent 1 classifier + metadata
# ─────────────────────────────────────────

def detect_domain(text: str) -> str:
    """
    Detect compliance domain from text using keywords.
    Returns domain label for Milvus metadata + Agent 1.
    """
    text_lower = text.lower()
    scores     = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[domain] = score

    if not scores:
        return "General"

    return max(scores, key=scores.get)

# ─────────────────────────────────────────
# PARENT LOOKUP HELPER
# ─────────────────────────────────────────

def _get_parent_text(collection_name: str, parent_id: str) -> str:
    """Fetch the full parent chunk text by id, from the correct
    RDS table depending on which collection this came from."""
    table = "document_chunks" if collection_name == COL_CIRCULARS else "policy_chunks"
    conn = get_db()
    c    = conn.cursor()
    c.execute(f"SELECT chunk_text FROM {table} WHERE id=%s", (int(parent_id),))
    row = c.fetchone()
    conn.close()
    return row['chunk_text'] if row else None

# ─────────────────────────────────────────
# TOOL 1 — search_similar()
# Called by Agent 2 with domain filter
# ─────────────────────────────────────────

def search_similar(query_text: str,
                   domain_filter: str = None,
                   n_results: int = 5,
                   collection_name: str = COL_POLICIES) -> list:
    """
    Find most similar chunks for a given query, searching at the
    CHILD level (precise) but returning each match's PARENT full
    text as context (broader), plus the matched child text too.

    Args:
        query_text      : circular text or domain query
        domain_filter   : domain label from Agent 1 (makes search smarter)
        n_results       : number of results to return
        collection_name : which Milvus collection to search

    Returns:
        list of dicts with text (parent), matched_child_text,
        metadata, similarity score
    """
    log.info("Searching [%s] domain=%s query=%s...",
             collection_name, domain_filter, query_text[:50])

    # Convert query to vector
    query_vector = get_embedding(query_text)
    if not query_vector:
        log.error("Could not embed query")
        return []

    col = get_collection(collection_name)

    if col.num_entities == 0:
        log.warning("Collection %s is empty", collection_name)
        return []

    n = min(n_results, col.num_entities)

    # All metadata fields to retrieve alongside the search result
    output_fields = [
        "document", "doc_id", "parent_id", "source",
        "title", "child_index", "domain", "filename"
    ]

    search_params = {
        "metric_type": "COSINE",
        "params"     : {"ef": 64}
    }

    # Build expr for optional domain filter
    expr = f'domain == "{domain_filter}"' if domain_filter else None

    results = []
    try:
        results = col.search(
            data          = [query_vector],
            anns_field    = "vector",
            param         = search_params,
            limit         = n,
            expr          = expr,
            output_fields = output_fields
        )
    except Exception as e:
        log.warning("Milvus search with expr failed: %s. Retrying without filter.", e)
        try:
            results = col.search(
                data          = [query_vector],
                anns_field    = "vector",
                param         = search_params,
                limit         = n,
                output_fields = output_fields
            )
        except Exception as err:
            log.error("Milvus search failed cleanly: %s", err)
            return []

    if not results:
        return []

    # Format results — swap matched CHILD text for its PARENT's full text,
    # giving the LLM broader context than the narrow 150-word slice that
    # actually matched the search
    matches = []
    for hit in results[0]:
        entity = hit.entity.fields if hasattr(hit.entity, "fields") else (hit.entity if isinstance(hit.entity, dict) else {})

        metadata = {
            "doc_id"     : entity.get("doc_id",      ""),
            "parent_id"  : entity.get("parent_id",   ""),
            "source"     : entity.get("source",      ""),
            "title"      : entity.get("title",       ""),
            "child_index": entity.get("child_index", ""),
            "domain"     : entity.get("domain",      ""),
            "filename"   : entity.get("filename",    ""),
        }

        child_text  = entity.get("document", "")
        parent_id   = metadata.get("parent_id")
        parent_text = _get_parent_text(collection_name, parent_id) if parent_id else None

        # Milvus COSINE score: higher = more similar (1.0 = identical)
        # Maintain same output contract as before: distance = 1 - similarity
        similarity = round(float(hit.score), 4)
        distance   = round(1.0 - similarity, 4)

        matches.append({
            "id"                : hit.id,
            "text"              : parent_text or child_text,
            "matched_child_text": child_text,
            "metadata"          : metadata,
            "distance"          : distance,
            "similarity"        : similarity
        })

    log.info("Found %d matches", len(matches))
    return matches

# ─────────────────────────────────────────
# TOOL 2 — calculate_drift()
# Called by Agent 2 after search_similar()
# Formula: 0.60 x semantic + 0.25 x policy + 0.15 x entity
# ─────────────────────────────────────────

def calculate_drift(circular_text: str,
                    policy_chunks: list) -> dict:
    """
    Calculate policy drift score.
    Optimised — fetches policy vectors from Milvus
    instead of re-embedding them via Ollama.
    Only 1 Ollama call per circular (for circular_text).
    """
    import spacy
    import numpy as np

    nlp = spacy.load("en_core_web_sm")

    if not policy_chunks:
        return {
            "drift_score"      : 0.0,
            "semantic_score"   : 0.0,
            "policy_score"     : 0.0,
            "entity_score"     : 0.0,
            "priority"         : "Archive",
            "action"           : "No policy chunks found",
            "affected_policies": []
        }

    # ── 1. embed circular text (1 Ollama call) ─────────
    circ_vector = get_embedding(circular_text[:2000])
    if not circ_vector:
        return {"error": "Could not embed circular text"}

    circ_vec = np.array(circ_vector)

    # ── 2. fetch policy vectors from Milvus ───────────
    # No Ollama calls — vectors already stored in Milvus
    collection = get_collection(COL_POLICIES)

    chunk_ids = [c["id"] for c in policy_chunks if c.get("id")]

    semantic_scores = []

    if chunk_ids:
        try:
            id_expr = _build_id_expr(chunk_ids)
            stored  = collection.query(
                expr          = id_expr,
                output_fields = ["id", "vector"]
            )

            for row in stored:
                vec = row.get("vector")
                if vec is not None and len(vec) > 0:
                    pv      = np.array(vec)
                    cos_sim = float(
                        np.dot(circ_vec, pv) /
                        (np.linalg.norm(circ_vec) *
                         np.linalg.norm(pv) + 1e-10)
                    )
                    semantic_scores.append(max(0, cos_sim))

        except Exception as e:
            log.warning("Milvus vector fetch failed: %s. "
                        "Falling back to re-embedding.", e)

    # fallback — if Milvus fetch failed, re-embed
    if not semantic_scores:
        log.info("Fallback: re-embedding policy chunks")
        for chunk in policy_chunks[:3]:
            pv = get_embedding(chunk["text"][:2000])
            if pv:
                pv      = np.array(pv)
                cos_sim = float(
                    np.dot(circ_vec, pv) /
                    (np.linalg.norm(circ_vec) *
                     np.linalg.norm(pv) + 1e-10)
                )
                semantic_scores.append(max(0, cos_sim))

    semantic_score = round(
        sum(semantic_scores) / len(semantic_scores), 4
    ) if semantic_scores else 0.0

    # ── 3. policy keyword match (25% weight) ────────────
    policy_keywords = [
        "regulation", "compliance", "circular",
        "amendment", "directions", "norms",
        "guidelines", "requirement", "shall", "must",
        "penalty", "violation", "reporting",
        "disclosure", "investor", "market", "sebi", "rbi"
    ]
    circ_lower      = circular_text.lower()
    all_policy_text = " ".join(
        c["text"] for c in policy_chunks
    ).lower()

    circ_hits   = sum(1 for kw in policy_keywords if kw in circ_lower)
    policy_hits = sum(1 for kw in policy_keywords if kw in all_policy_text)
    max_hits    = len(policy_keywords)

    policy_score = round(
        (circ_hits + policy_hits) / (2 * max_hits), 4
    )

    # ── 4. entity match (15% weight) ────────────────────
    doc1  = nlp(circular_text[:5000])
    doc2  = nlp(all_policy_text[:5000])

    ents1 = set(e.text.lower() for e in doc1.ents)
    ents2 = set(e.text.lower() for e in doc2.ents)

    if ents1 or ents2:
        common       = ents1.intersection(ents2)
        entity_score = round(
            len(common) / max(len(ents1 | ents2), 1), 4
        )
    else:
        entity_score = 0.0

    # ── 5. final drift score ────────────────────────────
    drift_score = round(
        0.60 * semantic_score +
        0.25 * policy_score   +
        0.15 * entity_score,
        4
    )

    # ── 6. priority ─────────────────────────────────────
    if drift_score >= 0.80:
        priority = "HIGH — P1"
        action   = "Immediate compliance action needed"
    elif drift_score >= 0.60:
        priority = "MEDIUM — P2"
        action   = "Review and update policy within 30 days"
    elif drift_score >= 0.40:
        priority = "LOW — P3"
        action   = "Monitor for future updates"
    else:
        priority = "Archive"
        action   = "No immediate action needed"

    # ── 7. affected policies ────────────────────────────
    affected = list(set([
        c["metadata"].get("filename", "unknown")
        for c in policy_chunks
        if c.get("metadata")
    ]))

    return {
        "drift_score"      : drift_score,
        "semantic_score"   : semantic_score,
        "policy_score"     : policy_score,
        "entity_score"     : entity_score,
        "priority"         : priority,
        "action"           : action,
        "affected_policies": affected
    }

# ─────────────────────────────────────────
# TEST FUNCTIONS
# ─────────────────────────────────────────

def test_search():
    """Test similarity search with domain filter."""
    print("\n" + "=" * 50)
    print("TEST 1: Search without domain filter")
    print("=" * 50)
    results = search_similar(
        "investment adviser certification NISM",
        n_results=3
    )
    for i, r in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"  File      : {r['metadata'].get('filename', r['metadata'].get('title',''))[:50]}")
        print(f"  Domain    : {r['metadata'].get('domain','')}")
        print(f"  Similarity: {r['similarity']}")
        print(f"  Text      : {r['text'][:100]}...")

    print("\n" + "=" * 50)
    print("TEST 2: Search WITH domain filter (Agent 2 style)")
    print("=" * 50)
    results = search_similar(
        "investment adviser certification NISM",
        domain_filter="Investment Advisory",
        n_results=3
    )
    for i, r in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"  File      : {r['metadata'].get('filename', r['metadata'].get('title',''))[:50]}")
        print(f"  Domain    : {r['metadata'].get('domain','')}")
        print(f"  Similarity: {r['similarity']}")
        print(f"  Text      : {r['text'][:100]}...")

def test_drift():
    """Test drift score calculation."""
    print("\n" + "=" * 50)
    print("TEST 3: Drift score calculation")
    print("=" * 50)

    circular = """SEBI has issued circular HO/38/12/11(5)2026 requiring
    all Persons Associated with Investment Advice (PAIA) who perform
    sales and non-core services to obtain NISM Series XXV-B certification.
    This replaces the previous requirement of NISM Series X-A and X-B
    for this category of staff. Effective immediately."""

    # get policy chunks
    policy_chunks = search_similar(
        circular,
        domain_filter="Investment Advisory",
        n_results=5
    )

    if not policy_chunks:
        print("No policy chunks found — trying without filter")
        policy_chunks = search_similar(circular, n_results=5)

    result = calculate_drift(circular, policy_chunks)

    print(f"\nDrift Score     : {result['drift_score']}")
    print(f"Semantic Score  : {result['semantic_score']} (60% weight)")
    print(f"Policy Score    : {result['policy_score']} (25% weight)")
    print(f"Entity Score    : {result['entity_score']} (15% weight)")
    print(f"Priority        : {result['priority']}")
    print(f"Action          : {result['action']}")
    print(f"Affected Policies: {result['affected_policies']}")

# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────

if __name__ == "__main__":

    # check ollama
    if not check_ollama():
        print("\nERROR: Start Ollama first with: ollama serve")
        exit(1)

    # check milvus
    if not check_milvus():
        print("\nERROR: Milvus not reachable.")
        print("Ensure SSH tunnel: ssh -N -L 19530:localhost:19530 student15@192.168.6.50 -p 22")
        exit(1)

    # embed circulars into collection 1
    embed_circulars()

    # embed policies into collection 2
    embed_policies()

    # run tests
    test_search()
    test_drift()

    print("\n[OK] Layer 3 complete. Milvus (GPU server) ready for Layer 4 agents.")