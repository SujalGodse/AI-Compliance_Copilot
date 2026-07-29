# ============================================================
# src/ingestion.py
# AI Compliance Copilot — Layer 1: Data Ingestion
# Member 1 — Data Engineer
#
# SCOPE: SEBI (RSS), RBI (RSS), IRDAI + PFRDA (manual folder watch)
#
# What this file does:
# 1. Fetches SEBI circulars via official RSS feed
# 2. Fetches RBI notifications via official RSS feed
# 3. Watches data/irdai and data/pfrda folders for manually
#    dropped PDFs (these regulators have no scrapable RSS/listing)
# 4. Filters only real circulars (removes enforcement noise)
# 5. Finds and downloads PDF for each circular
# 6. Deduplicates using SHA-256
# 7. Saves to SQLite queue
# ============================================================

import os
import re
import ssl
import hashlib
import psycopg2
import logging
import feedparser
import urllib.request
import http.cookiejar
from datetime import datetime

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(BASE_DIR, "logs", "ingestion.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

import sys
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
from db import get_db, init_all_tables

SEBI_RSS  = "https://www.sebi.gov.in/sebirss.xml"
SEBI_DIR  = os.path.join(BASE_DIR, "data", "sebi")

RBI_RSS   = "https://www.rbi.org.in/notifications_rss.xml"
RBI_DIR   = os.path.join(BASE_DIR, "data", "rbi")

IRDAI_DIR = os.path.join(BASE_DIR, "data", "irdai")
PFRDA_DIR = os.path.join(BASE_DIR, "data", "pfrda")

# only keep these URL patterns — real circulars only
SEBI_ALLOWED = [
    "/legal/circulars/",
    "/legal/master-circulars/",
    "/media-and-notifications/press-releases/",
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
# SSL HELPER
# ─────────────────────────────────────────

def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    return ctx



def strip_html(html_text):
    """Remove HTML tags and decode entities from RBI's embedded
    notification text, leaving clean plain text."""
    import html as html_module

    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_text,
                  flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html_module.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ─────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────

def init_db():
    """Create document_queue table on RDS PostgreSQL."""
    init_all_tables()
    log.info("Database ready.")

# ─────────────────────────────────────────
# SHA-256 DEDUPLICATION
# ─────────────────────────────────────────

def sha256_of_url(url):
    return hashlib.sha256(url.encode()).hexdigest()

def already_exists(sha256):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("SELECT id FROM document_queue WHERE sha256=%s", (sha256,))
    row  = cur.fetchone()
    conn.close()
    return row is not None

def save_to_queue(title, url, file_path, sha256, source="sebi"):
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO document_queue
            (source, title, url, file_path, sha256, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
        """, (source, title, url, file_path, sha256))
        conn.commit()
        log.info("Queued [%s]: %s", source.upper(), title[:80])
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        log.debug("Duplicate skipped.")
    finally:
        conn.close()

# ─────────────────────────────────────────
# FIND PDF URL FROM SEBI PAGE
# ─────────────────────────────────────────

def find_pdf_url(page_url):
    """Find direct PDF link from a SEBI circular page."""
    try:
        ctx = get_ssl_context()
        req = urllib.request.Request(
            page_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            html = r.read().decode("utf-8", errors="ignore")

        # sebi_data direct links — most reliable
        matches = re.findall(
            r'https://www\.sebi\.gov\.in/sebi_data[^\s"\'<>]+\.pdf',
            html, re.IGNORECASE
        )
        if matches:
            return matches[0]

        # fallback — any sebi PDF
        matches = re.findall(
            r'https://www\.sebi\.gov\.in[^\s"\'<>]+\.pdf',
            html, re.IGNORECASE
        )
        if matches:
            return matches[0]

    except Exception as e:
        log.warning("PDF search failed for %s: %s", page_url, e)
    return None

# ─────────────────────────────────────────
# DOWNLOAD PDF
# ─────────────────────────────────────────

def download_pdf(pdf_url: str, title: str, source: str = "sebi") -> str:
    """Download PDF from URL and upload directly to AWS S3."""
    try:
        ctx = get_ssl_context()
        req = urllib.request.Request(
            pdf_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            content = r.read()

        filename = pdf_url.split("/")[-1]
        if not filename.lower().endswith(".pdf"):
            filename = sha256_of_url(pdf_url)[:16] + ".pdf"

        # Stream directly to AWS S3
        try:
            from s3_utils import upload_bytes_to_s3
            s3_key = f"circulars/{source}_{filename}"
            s3_url = upload_bytes_to_s3(content, s3_key)
            log.info("Circular uploaded to S3: %s", s3_url)
            return s3_url
        except Exception as s3_err:
            log.warning("S3 upload failed (%s). Falling back to local disk...", s3_err)
            save_dir = os.path.join(BASE_DIR, "data", source)
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, filename)
            with open(save_path, "wb") as f:
                f.write(content)
            return save_path

    except Exception as e:
        log.warning("Download failed: %s", e)
        return None


# ─────────────────────────────────────────
# FETCH HISTORICAL SEBI CIRCULARS
# Directly from SEBI circulars listing page
# ─────────────────────────────────────────

def fetch_sebi_historical():
    """Fetch recent circulars directly from SEBI circulars page."""
    log.info("Fetching historical SEBI circulars...")

    circular_urls = [
        "https://www.sebi.gov.in/legal/circulars/jun-2026/norms-for-base-price-price-bands-call-auction-in-pre-open-session-and-close-out-procedure-for-exchange-traded-funds-etfs-_102121.html",
        "https://www.sebi.gov.in/legal/circulars/mar-2026/regulatory-reporting-by-aifs_100120.html",
        "https://www.sebi.gov.in/legal/circulars/feb-2026/categorization-and-rationalization-of-mutual-fund-schemes_99983.html",
        "https://www.sebi.gov.in/legal/circulars/mar-2026/addendum-to-sebi-circular-on-borrowing-by-mutual-funds_100560.html",
        "https://www.sebi.gov.in/legal/circulars/jan-2026/ease-of-doing-investment-special-window-for-transfer-and-dematerialisation-of-physical-securities_99411.html",
        "https://www.sebi.gov.in/legal/circulars/jan-2026/simplification-of-requirements-for-grant-of-accreditation-to-investors_99005.html",
        "https://www.sebi.gov.in/legal/circulars/jan-2026/compliance-reporting-formats-for-specialized-investment-funds-sifs-_98987.html",
        "https://www.sebi.gov.in/legal/circulars/jan-2026/specification-of-the-consequential-requirements-with-respect-to-amendment-of-securities-and-exchange-board-of-india-merchant-bankers-regulations-1992_98831.html",
        "https://www.sebi.gov.in/legal/circulars/jan-2026/ease-of-doing-investment-and-ease-of-doing-business-doing-away-with-requirement-of-issuance-of-letter-of-confirmation-loc-and-to-effect-direct-credit-of-securities-in-dematerialisation-account-o-_99421.html",
        "https://www.sebi.gov.in/legal/circulars/jan-2026/extension-of-timeline-for-implementation-of-additional-incentives-structure-for-distributors-for-onboarding-new-individual-investors-from-b-30-cities-and-women-investors_98962.html",
    ]

    new_count = 0
    for url in circular_urls:
        title = url.split("/")[-1]
        title = title.replace("-", " ").replace("_", " ")
        title = ' '.join(title.split()[:-1])
        title = title.title()

        sha = sha256_of_url(url)
        if already_exists(sha):
            log.debug("Already exists: %s", title[:50])
            continue

        file_path = None
        pdf_url   = find_pdf_url(url)
        if pdf_url:
            file_path = download_pdf(pdf_url, title)

        save_to_queue(title, url, file_path, sha)
        new_count += 1

    log.info("Historical: %d new circulars queued.", new_count)


# ─────────────────────────────────────────
# FIND PDF URL FROM RBI NOTIFICATION PAGE
# ─────────────────────────────────────────

def find_pdf_url_rbi(page_url):
    """Find direct PDF link from an RBI notification page."""
    try:
        ctx = get_ssl_context()
        req = urllib.request.Request(
            page_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            html = r.read().decode("utf-8", errors="ignore")

        matches = re.findall(
            r'https://rbidocs\.rbi\.org\.in[^\s"\'<>]+\.(?:pdf|PDF)',
            html
        )
        if matches:
            return matches[0]

    except Exception as e:
        log.warning("RBI PDF search failed for %s: %s", page_url, e)
    return None


# ─────────────────────────────────────────
# DOWNLOAD RBI PDF (session + Referer + validation)
# RBI's PDF host serves an HTML "enable JavaScript" page
# instead of the real PDF to plain script requests with no
# session/referer — this carries cookies from the notification
# page and verifies the response is a real PDF before saving.
# NOTE: currently unused by fetch_rbi() below since RBI still
# blocks even this approach after repeated requests — kept here
# for reference / future retry.
# ─────────────────────────────────────────

def download_pdf_rbi(pdf_url, referer, save_dir=RBI_DIR):
    """Download an RBI PDF, verifying it's a real PDF (not an interstitial page)."""
    try:
        ctx = get_ssl_context()
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar),
            urllib.request.HTTPSHandler(context=ctx)
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": referer,
        }

        # visit the notification page first to pick up session cookies
        opener.open(urllib.request.Request(referer, headers=headers), timeout=30)

        # now fetch the actual PDF, with the session cookies + Referer set
        req = urllib.request.Request(pdf_url, headers=headers)
        with opener.open(req, timeout=30) as r:
            content = r.read()

        if not content.startswith(b"%PDF"):
            log.warning("RBI response is not a real PDF (got HTML/JS interstitial): %s", pdf_url)
            return None

        filename = pdf_url.split("/")[-1]
        if not filename.lower().endswith(".pdf"):
            filename = sha256_of_url(pdf_url)[:16] + ".pdf"

        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        with open(save_path, "wb") as f:
            f.write(content)

        log.info("Downloaded (verified real PDF): %s", filename)
        return save_path

    except Exception as e:
        log.warning("RBI download failed: %s", e)
        return None


# ─────────────────────────────────────────
# FETCH RBI RSS
# PDF download is NOT attempted automatically — RBI's PDF host
# actively blocks automated downloads (connection resets after
# repeated requests). Circulars are queued with file_path=None;
# drop the matching PDF into data/rbi manually, then run
# folder_watch("rbi", RBI_DIR) to pick it up (see MAIN section).
# ─────────────────────────────────────────

def fetch_rbi():
    """Fetch RBI notifications RSS and queue new circulars.
    RBI embeds the FULL notification text directly in the RSS
    <description> field — no PDF download needed, avoiding
    RBI's anti-bot blocking entirely."""
    log.info("Fetching RBI notifications RSS feed...")
    try:
        ctx     = get_ssl_context()
        handler = urllib.request.HTTPSHandler(context=ctx)
        feed    = feedparser.parse(RBI_RSS, handlers=[handler])

        new_count = 0
        for entry in feed.entries:
            title       = entry.get("title", "Untitled").strip()
            url         = entry.get("link",  "").strip()
            description = entry.get("description", "")

            if not url:
                continue

            sha = sha256_of_url(url)
            if already_exists(sha):
                log.debug("Already exists: %s", title[:50])
                continue

            file_path  = None
            clean_text = strip_html(description) if description else ""

            if len(clean_text.split()) >= 30:
                os.makedirs(RBI_DIR, exist_ok=True)
                filename  = sha[:16] + ".txt"
                file_path = os.path.join(RBI_DIR, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(clean_text)
                log.info("Saved RBI text: %s", filename)
            else:
                log.warning("RBI entry has insufficient text, skipping content: %s", title[:60])

            save_to_queue(title, url, file_path, sha, source="rbi")
            new_count += 1

        log.info("RBI: %d new circulars queued.", new_count)

    except Exception as e:
        log.error("RBI RSS fetch failed: %s", e)

# ─────────────────────────────────────────
# FOLDER WATCHER — IRDAI / PFRDA
# Their sites have no scrapable RSS/listing,
# so circulars are dropped manually into
# data/irdai or data/pfrda and picked up here.
# ─────────────────────────────────────────

def folder_watch(source, watch_dir):
    """Queue any PDFs sitting in watch_dir that aren't already tracked."""
    log.info("Scanning %s folder for new PDFs...", source.upper())
    os.makedirs(watch_dir, exist_ok=True)

    new_count = 0
    for filename in sorted(os.listdir(watch_dir)):
        if not filename.lower().endswith(".pdf"):
            continue

        file_path = os.path.join(watch_dir, filename)
        # no source URL for manually-dropped files, so dedupe on
        # source+filename instead of a URL hash
        sha = hashlib.sha256(f"{source}:{filename}".encode()).hexdigest()

        if already_exists(sha):
            continue

        title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
        save_to_queue(title, None, file_path, sha, source=source)
        new_count += 1

    log.info("%s: %d new PDFs queued from folder.", source.upper(), new_count)


# ─────────────────────────────────────────
# FETCH SEBI RSS
# ─────────────────────────────────────────

def fetch_sebi():
    """Fetch SEBI RSS and queue new circulars."""
    log.info("Fetching SEBI RSS feed...")
    try:
        ctx     = get_ssl_context()
        handler = urllib.request.HTTPSHandler(context=ctx)
        feed    = feedparser.parse(SEBI_RSS, handlers=[handler])

        new_count = 0
        for entry in feed.entries:
            title = entry.get("title", "Untitled").strip()
            url   = entry.get("link",  "").strip()

            if not url:
                continue

            # filter — only real circulars
            if not any(p in url for p in SEBI_ALLOWED):
                continue

            # deduplication
            sha = sha256_of_url(url)
            if already_exists(sha):
                log.debug("Already exists: %s", title[:50])
                continue

            # find and download PDF
            file_path = None
            pdf_url   = find_pdf_url(url)
            if pdf_url:
                file_path = download_pdf(pdf_url, title)

            save_to_queue(title, url, file_path, sha)
            new_count += 1

        log.info("SEBI: %d new circulars queued.", new_count)

    except Exception as e:
        log.error("SEBI RSS fetch failed: %s", e)

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    fetch_sebi()                       # latest from RSS
    fetch_sebi_historical()            # historical circulars
    fetch_rbi()                        # RBI notifications RSS (metadata only)
    folder_watch("rbi", RBI_DIR)       # pick up manually-dropped RBI PDFs
    # IRDAI/PFRDA folder watching parked for now — no RSS/listing
    # available for these regulators yet; revisit later
    # folder_watch("irdai", IRDAI_DIR)
    # folder_watch("pfrda", PFRDA_DIR)
    log.info("Ingestion complete.")