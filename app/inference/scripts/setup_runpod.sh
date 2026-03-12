#!/usr/bin/env bash
# RunPod one-shot setup: pull repo, install system deps, PyTorch, SAM 3, app deps, then start server.
# Usage: bash scripts/setup_runpod.sh
# Optional env: REPO_ROOT, GIT_REPO_URL (required only when repo doesn't exist)

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/workspace/framesense-monorepo}"
INFERENCE_DIR="${REPO_ROOT}/app/inference"
SAM3_URL="${SAM3_URL:-https://github.com/facebookresearch/sam3.git}"
PYTORCH_INDEX="https://download.pytorch.org/whl/cu126"

echo "=== FrameSense inference – RunPod setup ==="
echo "REPO_ROOT=$REPO_ROOT"

# --- 1. Clone or pull repo ---
if [[ -d "$REPO_ROOT/.git" ]]; then
  echo "--- Pulling latest FrameSense repo ---"
  git -C "$REPO_ROOT" pull
else
  if [[ -z "${GIT_REPO_URL:-}" ]]; then
    echo "ERROR: No repo at $REPO_ROOT and GIT_REPO_URL not set."
    echo "Example: export GIT_REPO_URL=https://github.com/YOUR_USER/framesense-monorepo.git"
    exit 1
  fi
  echo "--- Cloning FrameSense repo ---"
  git clone "$GIT_REPO_URL" "$REPO_ROOT"
fi

# --- 2. System deps (ffmpeg, git) ---
echo "--- Installing system packages ---"
apt-get update -qq
apt-get install -y -qq ffmpeg git || true

# --- 3. PyTorch with CUDA ---
echo "--- Installing PyTorch (CUDA 12.6) ---"
pip install --no-cache-dir torch==2.7.0 torchvision torchaudio --index-url "$PYTORCH_INDEX"

# --- 4. SAM 3 from source ---
echo "--- Installing SAM 3 from source ---"
SAM3_TMP="/tmp/sam3-$$"
git clone --depth 1 "$SAM3_URL" "$SAM3_TMP"
pip install --no-cache-dir "$SAM3_TMP"
rm -rf "$SAM3_TMP"

# --- 5. App requirements ---
echo "--- Installing inference app requirements ---"
pip install --no-cache-dir -r "$INFERENCE_DIR/requirements.txt"

# --- 6. .env for HF token ---
if [[ ! -f "$INFERENCE_DIR/.env" ]]; then
  if [[ -f "$INFERENCE_DIR/.env.example" ]]; then
    cp "$INFERENCE_DIR/.env.example" "$INFERENCE_DIR/.env"
    echo "--- Created $INFERENCE_DIR/.env from .env.example – set HF_TOKEN for SAM 3 ---"
  fi
fi

# --- 7. Start server ---
echo "=== Setup done. Starting inference server on 0.0.0.0:8000 ==="
cd "$INFERENCE_DIR"
exec uvicorn main:app --host 0.0.0.0 --port 8000
