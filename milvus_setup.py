"""
milvus_setup.py
===============
One-time setup and connectivity verification script for the Milvus GPU server.

What this script does:
  1. Checks if Milvus port 19530 is reachable on localhost (i.e. SSH tunnel is up).
  2. If not reachable — optionally auto-spawns the SSH tunnel.
  3. Connects to Milvus and lists existing collections.
  4. Prints Docker install instructions for the GPU server if Milvus is not running.

Run once before starting the application:
  python milvus_setup.py

SSH Tunnel command (run in a separate terminal, or let this script auto-spawn it):
  ssh -N -L 19530:localhost:19530 -L 9091:localhost:9091 student15@192.168.6.50 -p 22
"""

import os
import sys
import time
import socket
import subprocess

# ─────────────────────────────────────────
# CONFIG (reads from .env if present)
# ─────────────────────────────────────────

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional

MILVUS_HOST     = os.getenv("MILVUS_HOST",     "localhost")
MILVUS_PORT     = int(os.getenv("MILVUS_PORT", "19530"))
GPU_SERVER_HOST = os.getenv("GPU_SERVER_HOST", "192.168.6.50")
GPU_SERVER_PORT = int(os.getenv("GPU_SERVER_PORT", "22"))
GPU_SERVER_USER = os.getenv("GPU_SERVER_USER", "student15")

# ─────────────────────────────────────────
# PORT CHECK
# ─────────────────────────────────────────

def check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if host:port is reachable within timeout seconds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

# ─────────────────────────────────────────
# SSH TUNNEL
# ─────────────────────────────────────────

def ensure_milvus_tunnel(auto_spawn: bool = False) -> bool:
    """
    Verify SSH tunnel to GPU server is active (Manual Mode).
    If auto_spawn=True, optionally spawns it in the background.
    Returns True if Milvus port is reachable.
    """
    if check_port(MILVUS_HOST, MILVUS_PORT):
        print(f"[OK] Milvus port {MILVUS_PORT} already reachable at {MILVUS_HOST}:{MILVUS_PORT}")
        return True

    print(f"[!] Milvus port {MILVUS_PORT} is not reachable on {MILVUS_HOST}.")
    print(f"    Since you are managing the SSH tunnel MANUALLY, please open a separate terminal and run:\n"
          f"    ssh -N -L {MILVUS_PORT}:localhost:{MILVUS_PORT} {GPU_SERVER_USER}@{GPU_SERVER_HOST} -p {GPU_SERVER_PORT}")

    if not auto_spawn:
        return False

    print(f"    Spawning SSH tunnel to {GPU_SERVER_USER}@{GPU_SERVER_HOST}:{GPU_SERVER_PORT} ...")
    cmd = [
        "ssh", "-N",
        "-L", f"{MILVUS_PORT}:localhost:{MILVUS_PORT}",
        "-L", "9091:localhost:9091",
        f"{GPU_SERVER_USER}@{GPU_SERVER_HOST}",
        "-p", str(GPU_SERVER_PORT)
    ]
    try:
        subprocess.Popen(cmd,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        time.sleep(3)   # give SSH time to establish
    except FileNotFoundError:
        print("[ERR] `ssh` not found. Install OpenSSH or add it to PATH.")
        return False
    except Exception as e:
        print(f"[ERR] Failed to spawn SSH tunnel: {e}")
        return False

    if check_port(MILVUS_HOST, MILVUS_PORT):
        print(f"[OK] SSH tunnel established! Milvus reachable at {MILVUS_HOST}:{MILVUS_PORT}")
        return True
    else:
        print("[!] SSH tunnel started but Milvus still not reachable.")
        print("    Ensure Milvus Lite is running on the GPU server and listening on port 19530.")
        print("    See the instructions printed below.\n")
        return False

# ─────────────────────────────────────────
# MILVUS CONNECTION CHECK
# ─────────────────────────────────────────

def check_milvus_connection() -> bool:
    """Connect to Milvus and list collections. Returns True on success."""
    try:
        from pymilvus import connections, utility
        connections.connect(
            alias   = "setup_check",
            host    = MILVUS_HOST,
            port    = MILVUS_PORT,
            timeout = 10
        )
        cols = utility.list_collections(using="setup_check")
        print(f"[OK] Milvus connected. Existing collections: {cols if cols else '(none yet)'}")
        connections.disconnect("setup_check")
        return True
    except Exception as e:
        print(f"[ERR] Milvus connection failed: {e}")
        return False

# ─────────────────────────────────────────
# MILVUS LITE & MANUAL TUNNEL INSTRUCTIONS
# ─────────────────────────────────────────

MILVUS_LITE_INSTRUCTIONS = """
+--------------------------------------------------------------------------+
|  MILVUS LITE (GPU Server) -- Manual SSH Tunnel Setup                     |
+--------------------------------------------------------------------------+
|                                                                          |
|  1. Ensure Milvus Lite is running and listening on port 19530 on the     |
|     GPU server (192.168.6.50).                                           |
|                                                                          |
|  2. On your LOCAL Windows machine -- open the SSH tunnel MANUALLY:       |
|     Open a new PowerShell / Command Prompt terminal and run:             |
|                                                                          |
|     ssh -N -L 19530:localhost:19530 student15@192.168.6.50 -p 22         |
|                                                                          |
|     (Keep that terminal window open while working with the app).         |
|                                                                          |
|  3. Re-run this script to verify connection:                             |
|     python milvus_setup.py                                               |
|                                                                          |
+--------------------------------------------------------------------------+
"""

# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  AI Compliance Copilot -- Milvus GPU Server Setup Check")
    print("=" * 60)
    print(f"  Target  : {MILVUS_HOST}:{MILVUS_PORT} (SSH-tunnelled from {GPU_SERVER_HOST})")
    print(f"  Mode    : Manual SSH Tunnel")
    print()

    reachable = ensure_milvus_tunnel(auto_spawn=False)

    if reachable:
        ok = check_milvus_connection()
        if ok:
            print()
            print("[OK] Milvus is fully operational. You can now run:")
            print("     python src/embeddings.py      # embed all circulars + policies")
            print("     uvicorn src.api:app --reload  # start FastAPI")
        else:
            print()
            print(MILVUS_LITE_INSTRUCTIONS)
            sys.exit(1)
    else:
        print()
        print(MILVUS_LITE_INSTRUCTIONS)
        sys.exit(1)
