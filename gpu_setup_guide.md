# PatentMind AI — Comprehensive GPU Server Setup & Troubleshooting Guide

This guide provides step-by-step instructions for configuring local and remote GPU acceleration (including HPC environments like **CDAC PARAM Shavak**), setting up **Ollama** and **PaddleOCR**, configuring SSH tunnels, and resolving common GPU runtime errors.

---

## 🏗️ 1. Architecture Overview & Hardware Requirements

### System Stack & GPU Roles
- **Local / Remote Server**: CDAC PARAM Shavak (`192.168.6.50:22`) or Local NVIDIA GPU.
- **LLM Inference Engine**: Ollama serving `Qwen3-4B` / `qwen2.5:3b` (GPU accelerated).
- **OCR Document Processing**: PaddleOCR (`PP-OCRv4` + `PP-StructureV2` with CUDA).
- **Embedding Acceleration**: PyTorch + `SentenceTransformers` (`all-MiniLM-L6-v2` 384-dim).

### Minimum GPU Hardware Requirements
| Component | Minimum Specification | Recommended Specification |
|-----------|-----------------------|---------------------------|
| **GPU VRAM** | 6 GB VRAM | 12 GB+ VRAM (NVIDIA RTX 3090 / A100 / CDAC PARAM Shavak) |
| **CUDA Version** | CUDA 11.8 | CUDA 12.1+ |
| **NVIDIA Driver** | Driver >= 525.xx | Driver >= 535.xx |
| **System RAM** | 16 GB DDR4 | 32 GB+ DDR4/DDR5 |

---

## ⚙️ 2. Step-by-Step GPU Environment Setup

### Step 1: Verify NVIDIA Driver & CUDA
Run `nvidia-smi` in PowerShell or Bash to ensure NVIDIA drivers and CUDA runtime are operational:
```bash
nvidia-smi
```
*Expected Output:*
```text
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 535.129.03              Driver Version: 535.129.03    CUDA Version: 12.2     |
|-------------------------------------+------------------------+--------------------------+
| GPU  Name                 Persistence-M | Bus-Id        Disp.A | Volatile Uncorr. ECC     |
|   0  NVIDIA A100-PCIE-40GB          Off | 00000000:01:00.0   Off |                    0     |
+-------------------------------------+------------------------+--------------------------+
```

---

### Step 2: Virtual Environment Setup
Create and activate Python 3.11 virtual environment:

```bash
# Clone & navigate to project
cd "C:\Users\Omkar\Downloads\Patent Basic"

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Linux/Bash)
source .venv/bin/activate
```

---

### Step 3: PyTorch & PaddlePaddle GPU Installation

#### A. Install PyTorch with CUDA Support
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

*Verification:*
```python
python -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('GPU Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

#### B. Install PaddlePaddle GPU Acceleration
```bash
pip install paddlepaddle-gpu -f https://www.paddlepaddle.org.cn/whl/windows/mkl/avx/stable.html
pip install paddleocr
```

---

### Step 4: Setting Up Ollama for LLM Inference

#### A. Install & Serve Ollama
Download Ollama from [ollama.com](https://ollama.com) or install via terminal:

```bash
# Start Ollama service on GPU host
ollama serve
```

#### B. Pull the Required PatentMind Models
```bash
# Pull 3B/4B Qwen Model for GPU inference
ollama pull qwen2.5:3b
# Or for higher VRAM GPUs (8GB+):
ollama pull qwen3:4b
```

#### C. Verify Ollama API Endpoint
```bash
curl http://127.0.0.1:11434/api/tags
```

---

### Step 5: Setting Up Remote GPU Server (CDAC PARAM Shavak)

If using a remote GPU server (e.g., `student15@192.168.6.50`):

#### A. SSH Port Forwarding (Ollama & Remote Server)
Execute background port forwarding on your local machine to securely access the remote GPU server's Ollama instance over port `11434`:

```powershell
# Windows PowerShell SSH Tunneling
ssh -N -L 11434:localhost:11434 student15@192.168.6.50 -p 22
```

#### B. Environment Configuration (`.env`)
Update `patentmind/.env` and `.env` with GPU server details:
```env
# GPU Server & LLM Configuration
GPU_SERVER_HOST=192.168.6.50
GPU_SERVER_PORT=22
GPU_SERVER_USER=student15
OLLAMA_BASE_URL=http://127.0.0.1:11434
GROQ_API_KEY=gsk_YOUR_GROQ_API_KEY_HERE
```

---

## ⚡ 3. Dual GPU Pipeline Rule

> [!IMPORTANT]
> **Sequential Batch Rule for Limited VRAM GPUs (< 12GB):**
> Do NOT execute PaddleOCR high-resolution PDF rendering simultaneously with Qwen3-4B Ollama LLM inference on the same GPU. 
> 
> **Correct Sequential Workflow:**
> 1. `python -m patentmind.processing.pipeline` (OCR & Text Extraction Stage)
> 2. `python -m patentmind.embeddings.pipeline` (Qdrant Vector Embedding Stage)
> 3. `python start_all_services.py` (FastAPI Server & LLM RAG Query Stage)

---

## 🛠️ 4. Comprehensive GPU Troubleshooting & Error Resolution Matrix

### Error 1: `CUDA out of memory (OOM)` / `RuntimeError: CUDA error: out of memory`

#### 🔴 Symptom:
```text
torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.40 GiB (GPU 0; 8.00 GiB total capacity; 6.10 GiB already allocated).
```

#### 🔍 Root Cause:
Multiple processes (e.g., PyTorch embeddings + PaddleOCR + Ollama) are competing for GPU memory concurrently.

#### ✅ Step-by-Step Fix:
1. **Reduce Ollama Context & Parallel Instances**:
   Set environment variable before running Ollama:
   ```bash
   set OLLAMA_NUM_PARALLEL=1
   set OLLAMA_MAX_LOADED_MODELS=1
   ```
2. **Clear PyTorch VRAM Cache in Python**:
   Add cache release inside memory-intensive loops:
   ```python
   import torch
   if torch.cuda.is_available():
       torch.cuda.empty_cache()
   ```
3. **Use PyMuPDF Native Text Layer First**:
   Ensure `patentmind/processing/ocr_engine.py` extracts native PDF vector text layers directly, only triggering PaddleOCR when page character count is `< 100`.

---

### Error 2: `PaddlePaddle / PaddleOCR Initialization Failed` or `No matching distribution found for paddlepaddle`

#### 🔴 Symptom:
```text
ERROR: Could not find a version that satisfies the requirement paddlepaddle
[yellow]PaddleOCR initialization failed: ModuleNotFoundError: No module named 'paddle'[/yellow]
```

#### 🔍 Root Cause:
`paddlepaddle` wheel binary mismatch with specific Python versions (e.g. Python 3.11+ on Windows without matching C++ runtime).

#### ✅ Step-by-Step Fix:
1. **Install Direct Wheel for Windows Python 3.11**:
   ```bash
   pip install paddlepaddle -f https://www.paddlepaddle.org.cn/whl/windows/mkl/avx/stable.html
   ```
2. **Automatic System Graceful Fallback**:
   PatentMind AI incorporates a clean fallback mechanism. If PaddleOCR is unavailable or fails to initialize, `ocr_engine.py` automatically falls back to **PyMuPDF (`fitz`) text extraction**:
   ```python
   # Fallback snippet inside ocr_engine.py
   if not self.model_loaded or not self.ocr:
       return doc[page_num - 1].get_text()
   ```

---

### Error 3: `Ollama Service Connection Refused` (`http://127.0.0.1:11434`)

#### 🔴 Symptom:
```text
[!] Ollama service not responding at http://127.0.0.1:11434.
OllamaUnavailableError: Connection refused
```

#### 🔍 Root Cause:
The local `ollama serve` process is stopped, or SSH port forwarding for the remote GPU server disconnected.

#### ✅ Step-by-Step Fix:
1. **Restart Local Ollama**:
   ```bash
   ollama serve
   ```
2. **Re-establish Remote SSH Tunnel**:
   ```powershell
   ssh -N -L 11434:localhost:11434 student15@192.168.6.50 -p 22
   ```
3. **Verify Automatic Groq LLM Failover**:
   PatentMind AI's `LLMRouter` (`patentmind/llm/router.py`) detects when Ollama is unreachable and automatically routes queries to **Groq Cloud API (`llama-3.3-70b-versatile`)** in `< 0.1` seconds without user interruption!

---

### Error 4: Windows AppLocker / WDAC Blocking C-Extension DLLs (`_regex.pyd` or `sentence_transformers`)

#### 🔴 Symptom:
```text
ImportError: DLL load failed while importing _regex: The organization used Windows AppLocker to block this app.
```

#### 🔍 Root Cause:
Windows Enterprise Security Policies (WDAC / AppLocker) prevent unsigned native C-extension DLLs from executing inside `.venv\Lib\site-packages`.

#### ✅ Step-by-Step Fix:
1. **Automatic CPU Deterministic Encoder Fallback**:
   PatentMind AI catches DLL import exceptions in `patentmind/embeddings/encoder.py` and switches seamlessly to `DeterministicHashEncoder`.
2. **Verify Encoder Status**:
   `DeterministicHashEncoder` generates consistent 384-dimensional dense vectors using SHA-256 seed projection, ensuring 100% vector store compatibility without native C-DLL execution:
   ```python
   # Fallback encoder trigger in encoder.py
   try:
       from sentence_transformers import SentenceTransformer
   except Exception:
       from patentmind.embeddings.encoder import DeterministicHashEncoder
       return DeterministicHashEncoder()
   ```

---

### Error 5: Windows `cp1252` Console `UnicodeEncodeError` (`\u2713`, `\U0001f680`)

#### 🔴 Symptom:
```text
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 0: character maps to <undefined>
```

#### 🔍 Root Cause:
Windows Command Prompt / PowerShell defaults to `cp1252` encoding, failing when terminal output contains UTF-8 emojis or checkmarks.

#### ✅ Step-by-Step Fix:
1. **Set Python UTF-8 Encoding Environment Variable**:
   ```powershell
   $env:PYTHONIOENCODING="utf-8"
   ```
2. **Use ASCII-Safe Console Tags**:
   All logging tags in `start_all_services.py` are updated to ASCII-safe markers:
   - Success: `[OK]` (replacing `✓`)
   - Warning: `[!]` (replacing `⚠`)
   - Error: `[ERR]` (replacing `✕`)
   - Launch: `[START]` (replacing `🚀`)

---

### Error 6: `Port 8000 / 7474 / 7687 Already Allocated` (`[Errno 10048]`)

#### 🔴 Symptom:
```text
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000): only one usage of each socket address is permitted
```

#### 🔍 Root Cause:
A previous background FastAPI process or Neo4j container is already bound to port 8000, 7474, or 7687.

#### ✅ Step-by-Step Fix:
1. **Identify & Terminate Occupying Process on Port 8000 (PowerShell)**:
   ```powershell
   # Find process ID owning port 8000
   Get-NetTCPConnection -LocalPort 8000 | Select-Object LocalPort, OwningProcess

   # Kill process by ID
   Stop-Process -Id <OwningProcess_ID> -Force
   ```
2. **Restart Master Launcher**:
   ```bash
   python start_all_services.py
   ```

---

## 📋 5. Summary Checklist for GPU Setup

- [x] Run `nvidia-smi` and confirm CUDA availability.
- [x] Activate `.venv` virtual environment.
- [x] Install CUDA PyTorch (`cu121`) & PaddleOCR.
- [x] Launch `ollama serve` and pull `qwen2.5:3b` / `qwen3:4b`.
- [x] Connect SSH Tunnel for remote GPU server `CDAC PARAM Shavak` (`192.168.6.50:22`).
- [x] Launch master orchestrator via `python start_all_services.py`.
