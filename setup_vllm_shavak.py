import os
import subprocess
import sys

VAR_TMP = "/var/tmp/student14"
VENV_DIR = os.path.join(VAR_TMP, "vllm_env")
HF_CACHE = os.path.join(VAR_TMP, "hf_cache")

print("============================================================")
print("       SETTING UP VLLM & 70B ENVIRONMENT ON CDAC SHAVAK     ")
print("============================================================")

print("\n1. Creating high-speed NVMe directories on /var/tmp/student14...")
os.makedirs(VENV_DIR, exist_ok=True)
os.makedirs(HF_CACHE, exist_ok=True)
print(f"   - Virtualenv Path: {VENV_DIR}")
print(f"   - Hugging Face Cache Path: {HF_CACHE}")

print("\n2. Creating Python Virtual Environment...")
if not os.path.exists(os.path.join(VENV_DIR, "bin", "python3")):
    subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
    print("   - Virtual environment created successfully.")
else:
    print("   - Virtual environment already exists.")

pip_bin = os.path.join(VENV_DIR, "bin", "pip")

print("\n3. Upgrading pip and installing vLLM + Ray...")
subprocess.run([pip_bin, "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)
print("   Installing vLLM engine (this may take 1-2 minutes)...")
subprocess.run([pip_bin, "install", "vllm", "ray"], check=True)

print("\n4. Creating vLLM 70B Server Launcher Script (run_vllm_70b.sh)...")
launch_script = f"""#!/bin/bash
export HF_HOME={HF_CACHE}
export CUDA_VISIBLE_DEVICES=0,1
export VLLM_WORKER_MULTIPROC_METHOD=spawn

source {VENV_DIR}/bin/activate

echo "============================================================"
echo "LAUNCHING VLLM 70B AWQ MODEL ON 2x NVIDIA A100 GPUs (PORT 8000)"
echo "============================================================"

python3 -m vllm.entrypoints.openai.api_server \\
    --model casperhansen/llama-3-70b-instruct-awq \\
    --tensor-parallel-size 2 \\
    --port 8000 \\
    --max-model-len 4096 \\
    --gpu-memory-utilization 0.90 \\
    --enforce-eager
"""

script_path = os.path.join(VAR_TMP, "run_vllm_70b.sh")
with open(script_path, "w") as f:
    f.write(launch_script)

os.chmod(script_path, 0o755)
print(f"   - Launcher script created at: {script_path}")

print("\n============================================================")
print("VLLM INSTALLATION COMPLETE! READY TO LAUNCH 70B MODEL!")
print("============================================================")
