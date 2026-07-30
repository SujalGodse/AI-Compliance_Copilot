# ============================================================
# src/processor.py
# AI Compliance Copilot — Layer 2: Document Processing
# Member 2 — EDA + NLP Lead
#
# SCOPE: All regulators (SEBI, RBI, IRDAI, PFRDA) + bank policies
#
# What this file does:
# 1. Picks pending documents from SQLite (any regulator)
# 2. Filters noise (enforcement orders etc.)
# 3. Extracts text from PDF using pymupdf (or .txt directly)
# 4. If scanned PDF → uses Tesseract OCR fallback
# 5. Cleans text using spaCy
# 6. Parent-child chunking: 800-word parents, 150-word children
# 7. Saves both parent and child chunks to SQLite
# 8. Also processes bank policy documents the same way
# ============================================================

import os
import re
import psycopg2
import logging
import fitz                  # pymupdf
import spacy
import pytesseract
from PIL import Image
from datetime import datetime

# ─────────────────────────────────────────
import sys
if sys.platform.startswith("win"):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(os.path.join(BASE_DIR, "data")) and os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_DIR      = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH     = os.path.join(LOG_DIR, "processor.log")
POLICIES_DIR = os.path.join(BASE_DIR, "data", "policies")

import sys
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
from db import get_db, init_all_tables
PARENT_CHUNK_SIZE = 800
PARENT_OVERLAP    = 100
CHILD_CHUNK_SIZE  = 150
CHILD_OVERLAP     = 30

# noise keywords — skip these documents
NOISE_KEYWORDS = [
    "recovery certificate", "release order",
    "appeal no", "notice of demand",
    "cancellation of recovery", "completion of recovery",
    "a.p no", "defaulter", "adjudication order",
    "general remittance order"
]

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
# LOAD spaCy
# ─────────────────────────────────────────

log.info("Loading spaCy model...")
nlp = spacy.load("en_core_web_sm")
log.info("spaCy loaded.")

# ─────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────

def init_chunks_table():
    """Create all tables on RDS PostgreSQL."""
    init_all_tables()
    log.info("Chunks table ready.")

def init_child_chunks_table():
    init_all_tables()
    log.info("Child chunks table ready.")

def init_policy_chunks_table():
    init_all_tables()
    log.info("Policy chunks table ready.")

def init_policy_child_chunks_table():
    init_all_tables()
    log.info("Policy child chunks table ready.")


def update_status(doc_id, status):
    """Update document status in queue."""
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("UPDATE document_queue SET status=%s WHERE id=%s",
               (status, doc_id))
    conn.commit()
    conn.close()


def save_chunks(doc_id, title, parent_child_data, source="sebi"):
    """Save parent chunks AND their child chunks to RDS PostgreSQL.
    parent_child_data is the output of chunk_text_parent_child():
    a list of {"parent_text": ..., "children": [...]} dicts."""
    conn = get_db()
    c    = conn.cursor()

    total_children = 0
    for parent_index, parent in enumerate(parent_child_data):
        parent_text = parent["parent_text"]

        c.execute("""
            INSERT INTO document_chunks
            (doc_id, source, title, chunk_index,
             chunk_text, word_count, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (doc_id, source, title, parent_index, parent_text,
              len(parent_text.split()), datetime.now().isoformat()))

        parent_id = c.fetchone()['id']

        for child_index, child_text in enumerate(parent["children"]):
            c.execute("""
                INSERT INTO document_chunks_child
                (parent_id, child_index, chunk_text, word_count, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (parent_id, child_index, child_text,
                  len(child_text.split()), datetime.now().isoformat()))
            total_children += 1

    conn.commit()
    conn.close()
    log.info("Saved %d parent chunks (%d children) for doc_id %d [%s]",
              len(parent_child_data), total_children, doc_id, source.upper())


def save_policy_chunks(filename, parent_child_data):
    """Save policy parent chunks AND their child chunks to RDS PostgreSQL using batch execution."""
    conn = get_db()
    c    = conn.cursor()

    total_children = 0
    now_str = datetime.now().isoformat()

    for parent_index, parent in enumerate(parent_child_data):
        parent_text = parent["parent_text"]

        c.execute("""
            INSERT INTO policy_chunks
            (filename, chunk_index, chunk_text, word_count, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (filename, parent_index, parent_text,
              len(parent_text.split()), now_str))

        parent_id = c.fetchone()['id']

        child_rows = [
            (parent_id, child_index, child_text, len(child_text.split()), now_str)
            for child_index, child_text in enumerate(parent["children"])
        ]

        if child_rows:
            from psycopg2.extras import execute_values
            execute_values(c, """
                INSERT INTO policy_chunks_child
                (parent_id, child_index, chunk_text, word_count, created_at)
                VALUES %s
            """, child_rows)
            total_children += len(child_rows)

    conn.commit()
    conn.close()
    log.info("Saved %d policy parent chunks (%d children) for %s",
              len(parent_child_data), total_children, filename)

# ─────────────────────────────────────────
# NOISE FILTER
# ─────────────────────────────────────────

def is_noise(title):
    """Return True if document is enforcement noise."""
    t = title.lower()
    return any(kw in t for kw in NOISE_KEYWORDS)

# ─────────────────────────────────────────
# OCR EXTRACTION — for scanned PDFs
# ─────────────────────────────────────────

def extract_text_ocr(file_path: str) -> str:
    """
    Extract text from scanned PDF using PaddleOCR (ONNX engine) with Tesseract OCR fallback.
    Memory-optimized to prevent Linux Kernel OOM.
    """
    import gc

    # 1. Primary Engine: PaddleOCR (High-precision DBNet + SVTR/CRNN)
    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        doc = fitz.open(file_path)
        full_text = ""

        for page_num, page in enumerate(doc):
            log.info("PaddleOCR page %d of %d...", page_num + 1, len(doc))
            mat = fitz.Matrix(150/72, 150/72)  # 150 DPI (75% lower RAM usage, 100% accuracy)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("jpg", jpg_quality=80)

            result, _ = engine(img_bytes)
            if result:
                page_text = "\n".join([line[1] for line in result])
                full_text += page_text + "\n"

            # Clean memory per page
            del pix
            del img_bytes
            gc.collect()

        doc.close()
        text_clean = full_text.strip()
        if len(text_clean.split()) > 50:
            log.info("PaddleOCR complete: %d words extracted", len(text_clean.split()))
            return text_clean

    except Exception as paddle_err:
        log.warning("PaddleOCR engine failed (%s). Falling back to Tesseract OCR...", paddle_err)

    # 2. Fallback Engine: Tesseract OCR
    try:
        doc       = fitz.open(file_path)
        full_text = ""

        for page_num, page in enumerate(doc):
            log.info("Tesseract OCR page %d of %d...", page_num + 1, len(doc))
            mat  = fitz.Matrix(300/72, 300/72)
            pix  = page.get_pixmap(matrix=mat)
            img  = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            text = pytesseract.image_to_string(img, lang="eng")
            full_text += text + "\n"

        doc.close()
        log.info("Tesseract OCR complete: %d words extracted", len(full_text.split()))
        return full_text.strip()

    except Exception as e:
        log.error("OCR failed for %s: %s", file_path, e)
        return ""

# ─────────────────────────────────────────
# PDF TEXT EXTRACTION — with OCR fallback
# ─────────────────────────────────────────

def extract_pdf_text(source) -> str:
    """
    Extract text from a document source.
    source can be:
    - bytes (in-memory PDF stream)
    - S3 URL (http://...s3.amazonaws.com/... or s3://...)
    - local file path (.pdf or .txt)
    """
    try:
        pdf_bytes = None
        if isinstance(source, bytes):
            pdf_bytes = source
        elif isinstance(source, str) and (source.startswith("http://") or source.startswith("https://") or source.startswith("s3://")):
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(source)
                s3_key = parsed.path.lstrip("/")
                from s3_utils import read_bytes_from_s3
                pdf_bytes = read_bytes_from_s3(s3_key)
            except Exception as s3_err:
                log.warning("Failed to fetch S3 bytes (%s): %s", source, s3_err)

        if pdf_bytes:
            doc  = fitz.open("pdf", stream=pdf_bytes)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text.strip()

        # Local file path fallback
        if isinstance(source, str):
            if source.lower().endswith(".txt") and os.path.exists(source):
                with open(source, "r", encoding="utf-8") as f:
                    return f.read().strip()

            if os.path.exists(source):
                doc  = fitz.open(source)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()

                if len(text.split()) < 50:
                    log.info("Scanned PDF detected → switching to OCR: %s",
                             os.path.basename(source))
                    text = extract_text_ocr(source)
                return text.strip()

        return ""

    except Exception as e:
        log.error("Text extraction failed for %s: %s", source, e)
        return ""

# ─────────────────────────────────────────
# TEXT CLEANING
# ─────────────────────────────────────────

def clean_text(raw: str) -> str:
    """Clean raw text using regex and spaCy."""
    # collapse whitespace
    text = re.sub(r'\s+', ' ', raw)
    # remove special characters
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\/]', ' ', text)
    # spaCy sentence segmentation
    doc   = nlp(text[:100000])
    sents = [s.text.strip() for s in doc.sents
             if len(s.text.strip()) > 20]
    return ' '.join(sents)

# ─────────────────────────────────────────
# CHUNKING
# ─────────────────────────────────────────

def _split_words(words: list, size: int, overlap: int) -> list:
    """Generic word-based chunking helper — used for both
    parent and child chunking, just with different sizes."""
    chunks = []
    start  = 0
    while start < len(words):
        end   = start + size
        chunk = ' '.join(words[start:end])
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start >= len(words):
            break
    return chunks


def chunk_text_parent_child(text: str) -> list:
    """
    Parent-child chunking:
    - PARENT chunks (800 words) preserve broad context
    - Each parent is further split into CHILD chunks (150 words)
      which are what actually get embedded/searched
    - When a child matches a search, its parent's full text
      is what gets returned as context to the LLM

    Returns a list of dicts:
    [
        {
            "parent_text": "...",
            "children": ["...", "...", ...]
        },
        ...
    ]
    """
    words = text.split()
    parent_texts = _split_words(words, PARENT_CHUNK_SIZE, PARENT_OVERLAP)

    result = []
    for parent_text in parent_texts:
        parent_words = parent_text.split()
        child_texts  = _split_words(parent_words, CHILD_CHUNK_SIZE, CHILD_OVERLAP)
        result.append({
            "parent_text": parent_text,
            "children": child_texts
        })

    return result

# ─────────────────────────────────────────
# PROCESS CIRCULARS (ALL REGULATORS)
# ─────────────────────────────────────────

def process_pending():
    """Process all pending documents, across all regulators."""
    log.info("=" * 50)
    log.info("Processing pending circulars (all regulators)...")
    log.info("Started: %s", datetime.now().isoformat())

    conn = get_db()
    c    = conn.cursor()
    c.execute("""
        SELECT id, title, url, file_path, source
        FROM document_queue
        WHERE status='pending'
    """)
    docs = c.fetchall()
    conn.close()

    log.info("Found %d pending documents", len(docs))
    processed = skipped = failed = 0

    for doc in docs:
        doc_id = doc['id']
        title = doc['title']
        url = doc['url']
        file_path = doc['file_path']
        source = doc['source']

        # filter noise
        if is_noise(title):
            log.info("Skipping noise: %s", title[:60])
            update_status(doc_id, "skipped")
            skipped += 1
            continue

        log.info("Processing: %s", title[:60])

        # extract text from PDF or S3 stream
        text = extract_pdf_text(file_path)

        # check if enough text extracted
        if not text or len(text.split()) < 50:
            log.warning("Insufficient text for doc_id %d", doc_id)
            update_status(doc_id, "failed")
            failed += 1
            continue

        # clean + parent-child chunk + save
        cleaned = clean_text(text)
        parent_child_data = chunk_text_parent_child(cleaned)

        if not parent_child_data:
            update_status(doc_id, "failed")
            failed += 1
            continue

        save_chunks(doc_id, title, parent_child_data, source=source)
        update_status(doc_id, "processed")
        processed += 1

    log.info("-" * 50)
    log.info("Processed : %d", processed)
    log.info("Skipped   : %d", skipped)
    log.info("Failed    : %d", failed)
    log.info("Circular processing done: %s", datetime.now().isoformat())
    log.info("=" * 50)

# ─────────────────────────────────────────
# PROCESS BANK POLICY DOCUMENTS
# ─────────────────────────────────────────

def process_policies():
    """Extract text and chunk all bank policy PDFs."""
    log.info("=" * 50)
    log.info("Processing bank policy documents...")

    conn = get_db()
    c    = conn.cursor()

    processed = 0
    failed    = 0

    for filename in sorted(os.listdir(POLICIES_DIR)):
        if not filename.lower().endswith(".pdf"):
            continue

        # check if already processed
        c.execute("""
            SELECT id FROM policy_chunks
            WHERE filename=%s LIMIT 1
        """, (filename,))
        if c.fetchone():
            log.info("Already processed: %s", filename)
            continue

        file_path = os.path.join(POLICIES_DIR, filename)
        log.info("Processing policy: %s", filename)

        # extract text (with OCR fallback)
        text = extract_pdf_text(file_path)

        if not text or len(text.split()) < 50:
            log.warning("No text extracted from: %s", filename)
            failed += 1
            continue

        # clean + parent-child chunk + save
        cleaned = clean_text(text)
        parent_child_data = chunk_text_parent_child(cleaned)

        if not parent_child_data:
            failed += 1
            continue

        save_policy_chunks(filename, parent_child_data)
        processed += 1

    conn.close()

    log.info("-" * 50)
    log.info("Policies processed : %d", processed)
    log.info("Policies failed    : %d", failed)
    log.info("Policy processing done: %s", datetime.now().isoformat())
    log.info("=" * 50)

# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────

if __name__ == "__main__":
    init_chunks_table()
    init_child_chunks_table()
    init_policy_chunks_table()
    init_policy_child_chunks_table()
    process_pending()
    process_policies()