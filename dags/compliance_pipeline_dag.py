from datetime import datetime, timedelta
from airflow import DAG
try:
    from airflow.providers.standard.operators.python import PythonOperator
except ImportError:
    from airflow.operators.python import PythonOperator

import sys
import os

# Add src directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, "src"))

def task_fetch_circulars():
    """Task 1: Fetch live regulatory circulars (SEBI & RBI) and stream master PDFs to AWS S3."""
    from ingestion import init_db, fetch_sebi, fetch_sebi_historical
    init_db()
    fetch_sebi()
    fetch_sebi_historical()
    print("✅ Task 1 Complete: Circulars fetched and stored in AWS S3 & RDS document queue.")

def task_preprocess_and_ocr():
    """Task 2: Extract text using PaddleOCR (with Tesseract fallback) and split into parent-child chunks."""
    from processor import init_chunks_table, init_policy_chunks_table, process_pending
    init_chunks_table()
    init_policy_chunks_table()
    process_pending()
    print("✅ Task 2 Complete: PaddleOCR text extraction & parent-child chunking finished.")

def task_embed_and_index_milvus():
    """Task 3: Generate 1024-d embeddings and index into Milvus vector database."""
    from embeddings import embed_circulars, embed_policies
    embed_circulars()
    embed_policies()
    print("✅ Task 3 Complete: Embeddings generated & indexed in Milvus.")

def task_run_multi_agent_audit():
    """Task 4: Run Multi-Agent System (Agent 1 Groq -> Agent 2 Gap RAG -> Agent 3 RDS Ticket Creation)."""
    from agents import run_pipeline
    run_pipeline()
    print("✅ Task 4 Complete: Multi-Agent compliance audit & ticket creation finished.")

default_args = {
    'owner': 'compliance_team',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'compliance_pipeline_workflow',
    default_args=default_args,
    description='Automated 6-hour regulatory compliance ingestion, PaddleOCR, Milvus vector indexing, and Multi-Agent audit pipeline',
    schedule='0 */6 * * *',  # Every 6 hours
    catchup=False,
)

t1 = PythonOperator(
    task_id='fetch_regulatory_circulars',
    python_callable=task_fetch_circulars,
    dag=dag,
)

t2 = PythonOperator(
    task_id='preprocess_and_ocr_documents',
    python_callable=task_preprocess_and_ocr,
    dag=dag,
)

t3 = PythonOperator(
    task_id='generate_embeddings_milvus',
    python_callable=task_embed_and_index_milvus,
    dag=dag,
)

t4 = PythonOperator(
    task_id='run_multi_agent_compliance_audit',
    python_callable=task_run_multi_agent_audit,
    dag=dag,
)

t1 >> t2 >> t3 >> t4
