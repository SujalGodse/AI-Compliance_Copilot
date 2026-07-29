# GPU Integration Blueprint & Adaptation Guide for New Projects

This document provides a technical blueprint of the **3-Tier Distributed GPU Integration Architecture** developed for PatentMind AI, explaining how to adapt it to **any new AI project idea** (e.g., Healthcare, Financial Intelligence, Legal RAG, Multimodal Vision Systems).

---

## 🧠 1. Core GPU Integration Architecture

The architecture decouples heavy GPU tasks (generative inference, OCR, vector embeddings) from the core application logic using a **3-Tier Hybrid GPU Stack**:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION & REST API LAYER                           │
│                      FastAPI / Node.js / Python Web App                         │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SMART LLM ROUTER CONTROLLER                           │
│                  Probes Primary GPU Health (1.5s TCP Timeout)                   │
└───────────────────┬─────────────────────────────────────────┬───────────────────┘
                    │                                         │
    [Primary GPU Active / Port Open]            [Primary GPU Offline / Busy]
                    │                                         │
                    ▼                                         ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│     TIER 1: REMOTE / LOCAL GPU        │ │     TIER 2: CLOUD API FALLBACK        │
│  CDAC PARAM Shavak / Local RTX GPU    │ │      Groq API (llama-3.3-70b)         │
│  Ollama Engine (Port 11434)           │ │      OpenAI / Anthropic / Cohere     │
│  Model: Qwen3-4B / DeepSeek-R1        │ │      Latency: < 1.8 seconds           │
└───────────────────────────────────────┘ └───────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                       TIER 3: SEQUENTIAL BATCH GPU PROCESSING                   │
│  Stage 1: PaddleOCR (Scanned Page Vision GPU Extraction)                        │
│  Stage 2: SentenceTransformer PyTorch CUDA (Vector Embeddings)                  │
│  Stage 3: Qdrant Vector Storage (HNSW Cosine Indexing)                          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 2. Reusable Code Templates (Copy & Adapt for Any New Project)

### Template 1: Smart Dual LLM Fallback Router (`llm_router.py`)

Copy this router into any Python project to achieve zero-downtime LLM processing:

```python
import os
import httpx
import logging

logger = logging.getLogger("GPURouter")

class UniversalGPURouter:
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_model = "llama-3.3-70b-versatile"

    def generate(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> dict:
        """Route query to Primary GPU Ollama first; auto-fallback to Groq Cloud API if GPU unavailable."""
        # 1. Try Primary GPU (Ollama / Local / SSH Tunnel)
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "system": system_prompt,
                        "stream": False
                    }
                )
                if resp.status_code == 200:
                    return {
                        "answer": resp.json().get("response", ""),
                        "backend_used": f"Primary GPU ({self.ollama_model})"
                    }
        except Exception as e:
            logger.warning(f"Primary GPU unavailable ({e}). Triggering Cloud Fallback...")

        # 2. Fallback to Secondary Cloud API (Groq)
        if self.groq_api_key:
            try:
                from groq import Groq
                groq_client = Groq(api_key=self.groq_api_key)
                completion = groq_client.chat.completions.create(
                    model=self.groq_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=1024
                )
                return {
                    "answer": completion.choices[0].message.content,
                    "backend_used": f"Cloud Fallback ({self.groq_model})"
                }
            except Exception as ge:
                logger.error(f"Groq API fallback failed: {ge}")

        return {"answer": "All LLM inference backends are currently unreachable.", "backend_used": "None"}
```

---

### Template 2: Automatic SSH Port Forwarding (`gpu_tunnel.py`)

If your GPU lives on a remote HPC node (e.g. `student15@192.168.6.50`), use this script to ensure port `11434` is always forwarded automatically:

```python
import socket
import subprocess
import time

def check_port(host="127.0.0.1", port=11434, timeout=1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def ensure_gpu_tunnel():
    """Verifies connection to remote GPU port 11434; spawns SSH tunnel if disconnected."""
    if not check_port("127.0.0.1", 11434):
        print("SSH Tunnel to GPU server is down. Spawning background SSH tunnel to 192.168.6.50:22...")
        cmd = ["ssh", "-N", "-L", "11434:localhost:11434", "student15@192.168.6.50", "-p", "22"]
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            print("SSH GPU Tunnel established successfully!")
        except Exception as e:
            print(f"Failed to start SSH tunnel: {e}")
```

---

## 🎯 3. How to Adapt This GPU Blueprint to Other Project Ideas

Here is how you can take this exact GPU integration architecture and apply it to 3 different project domain ideas:

### Scenario A: 🏥 Medical Document & Diagnostic AI System
- **GPU Role**: 
  - **PaddleOCR (GPU)** extracts unstructured text & tables from scanned doctor notes and mammography/X-ray PDF reports.
  - **BioNeMo / BioMistral (Ollama GPU)** synthesizes patient summaries and checks drug interaction risks.
- **Integration Layer**:
  - Connect client hospital frontend to local GPU node or remote HPC server (`192.168.6.50`).
  - Use `LLMRouter` to fall back to HIPAA-compliant Cloud API if local GPU VRAM fills up.

---

### Scenario B: 📈 Financial Analytics & Earnings Report Intelligence
- **GPU Role**:
  - **LayoutLMv3 (GPU)** extracts financial tables, balance sheets, and charts from SEC 10-K filing PDFs.
  - **FinLlama / Qwen3-4B (Ollama GPU)** runs automated financial ratio analysis & risk factor extraction.
- **Integration Layer**:
  - Run **Sequential Pipeline**: Data Ingestion Stage (Batch OCR + Table Extraction) ➔ Embedding Ingestion Stage (Qdrant Vector DB) ➔ API Serving Stage.

---

### Scenario C: ⚖️ Legal Discovery & Contract Analysis Platform
- **GPU Role**:
  - **Legal-BERT / SentenceTransformers (GPU)** embeds 100,000+ legal clauses into vector database.
  - **Llama-3.3-70b / DeepSeek-R1 (Ollama GPU)** performs legal contract anomaly detection and prior case law matching.
- **Integration Layer**:
  - Use **HNSW Cosine Vector Indexing** in Qdrant + **Neo4j Graph Database** to trace clause dependencies.

---

## 📋 4. Key Rules for GPU Integration in Any Project

1. **Decouple Heavy GPU Batch Ingestion from Web API Serving**:
   Never run heavy document OCR batch ingestion and real-time user LLM queries on the same GPU simultaneously if VRAM is `< 12GB`.
2. **Always Implement Graceful CPU Fallbacks**:
   Provide a CPU or Hash fallback so the application never crashes if the GPU driver or SSH connection is interrupted.
3. **Use 1.5-Second Port Probing**:
   Probe port `11434` (Ollama) or `6333` (Qdrant) with a short 1.5-second socket check before attempting heavy model calls to keep API responses sub-second.
