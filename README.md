# AI Compliance Copilot — Enterprise RAG & Multi-Agent Compliance Monitoring System

> **Bank of India · SEBI / RBI / IRDAI / PFRDA Monitoring**  
> An autonomous AI compliance audit platform that ingests regulatory circulars, extracts text via deep-learning PaddleOCR, indexes 1024-d embeddings into Milvus Vector DB, performs RAG gap analysis against internal bank policies, and creates compliance audit tickets in AWS RDS PostgreSQL.

---

## 🏗️ Architecture & Technology Stack

```text
  [SEBI / RBI Feeds] ──► [AWS S3 Document Storage]
                               │
                               ▼
                   [PaddleOCR / PyMuPDF Engine]
                               │
                               ▼
                   [1024-d BGE FastEmbed Vectors]
                               │
                               ▼
                [Milvus Vector DB & AWS RDS PostgreSQL]
                               │
                               ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                 MULTI-AGENT REASONING ENGINE                │
  │ Agent 1 (Groq) ──► Agent 2 (RAG Gap) ──► Agent 3 (RDS Tickets) │
  └────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
            [Apache Airflow 6-Hour DAG Scheduler]
                               │
                               ▼
            [React + Vite Unified Web Application]
```

### **Core Technologies:**
- **Frontend:** React 18, Vite, Custom Unified Design System, Axios, Chart.js
- **Backend:** FastAPI (Python), Gunicorn, Uvicorn, Pydantic
- **Relational DB:** AWS RDS PostgreSQL (Tickets, circulars, policy chunks, and audit logs)
- **Vector DB:** Milvus / Milvus Lite (1024-dimensional FastEmbed BGE vectors)
- **Document Storage:** AWS S3 (`compliance-frontend-sujal-2026`) for master policy PDFs & circulars
- **OCR Engine:** PaddleOCR (Baidu DBNet Detection + SVTR Recognition via ONNX Runtime) with Tesseract OCR fallback
- **AI / LLM Engine:** Groq API (`llama-3.1-8b-instant`)
- **Multi-Agent Engine:** LangGraph 3-Agent Workflow
- **Pipeline Orchestration:** Apache Airflow DAG (`compliance_pipeline_workflow`) running 6-hour automated ETL schedule

---

## 🚀 Key Features

1. **Automated Live Regulatory Ingestion:** Streams SEBI and RBI regulatory RSS circular feeds directly into AWS S3 and AWS RDS PostgreSQL.
2. **Deep Learning PaddleOCR Pipeline:** Handles scanned PDFs, multi-column guidelines, and complex banking tables at high speed (< 1s per page) with fallback to Tesseract OCR.
3. **1024-d Vector Embeddings & RAG:** FastEmbed 1024-dimensional embeddings indexed into Milvus collections (`bank_policies` & `sebi_circulars`).
4. **Multi-Agent Reasoning Workflow:**
   - **Agent 1 (Groq Classifier):** Categorizes circulars (AIF, Mutual Funds, KYC, Lending) and assigns risk priorities.
   - **Agent 2 (RAG Gap Analyzer):** Searches Milvus vector DB for relevant policy clauses and computes drift scores.
   - **Agent 3 (Ticket Generator):** Writes structured compliance tickets and audit trails to AWS RDS PostgreSQL.
5. **Apache Airflow 6-Hour Scheduler:** Fully orchestrated DAG running end-to-end ingestion, OCR, embedding, and Multi-Agent audit automatically every 6 hours.
6. **Unified Web Dashboard:** Modern React UI for dashboard analytics, ticket management, circular viewer, bank policy uploader, audit trails, RAGAS evaluations, and Ask AI RAG chatbot.

---

## 📂 Project Structure

```text
├── dags/
│   └── compliance_pipeline_dag.py   # Apache Airflow DAG (6-hour ETL schedule)
├── src/
│   ├── api.py                       # FastAPI Backend REST API
│   ├── agents.py                    # 3-Agent Multi-Agent Reasoning Engine
│   ├── processor.py                 # PaddleOCR & Parent-Child Text Chunker
│   ├── embeddings.py                # FastEmbed 1024-d & Milvus Vector DB client
│   ├── ingestion.py                 # SEBI & RBI Live Regulatory Ingestion
│   ├── db.py                        # AWS RDS PostgreSQL connection pool
│   └── s3_utils.py                  # AWS S3 Boto3 Upload & Management
├── frontend/                        # React + Vite Web Application
│   ├── src/
│   │   ├── pages/                   # Dashboard, Tickets, Circulars, Policies, Ask AI, RAGAS
│   │   ├── components/              # StatCard, DriftChart, Sidebar, Header
│   │   └── index.css                # Unified Design System
│   └── dist/                        # Compiled Production Build Assets
├── requirements.txt                 # Python Dependencies
├── README.md                        # Documentation
└── .gitignore                       # Git Exclusion Rules
```

---

## 💻 Local Setup & Run Guide

### 1. Clone & Install Dependencies:
```bash
git clone https://github.com/SujalGodse/AI-Compliance_Copilot.git
cd AI-Compliance_Copilot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt
```

### 2. Start Services:
```bash
# Start FastAPI Backend
python src/api.py

# Start React Frontend (In another terminal)
cd frontend
npm install
npm run dev
```

### 3. Run Apache Airflow DAG:
```bash
export AIRFLOW_HOME=$(pwd)/airflow
airflow dags trigger compliance_pipeline_workflow
```

---

## 🔒 Security & Environment Configuration

Ensure `.env` contains your AWS RDS, AWS S3 credentials, and Groq API key:
```env
DB_HOST=compliance-db.c7a8k0isqxao.ap-south-1.rds.amazonaws.com
DB_NAME=compliance
DB_USER=postgres
DB_PASSWORD=YOUR_PASSWORD
DB_PORT=5432
GROQ_API_KEY=YOUR_GROQ_KEY
AWS_ACCESS_KEY_ID=YOUR_AWS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET
AWS_REGION=ap-south-1
S3_BUCKET_NAME=compliance-frontend-sujal-2026
```
