#!/usr/bin/env bash
# Helper script to download SAM-3D Objects checkpoints from Hugging Face.
#
# Prerequisites:
#   - HF_TOKEN environment variable exported, OR `hf auth login` has been run.
#   - `huggingface_hub` CLI installed in this environment.
#
# Usage:
#   export HF_TOKEN=your_hf_token_here
#   SAM3D_CHECKPOINT_PATH=checkpoints/hf ./scripts/setup_checkpoints.sh

set -euo pipefail

TARGET_DIR="${SAM3D_CHECKPOINT_PATH:-checkpoints/hf}"

echo "Downloading SAM-3D Objects checkpoints into: ${TARGET_DIR}"
mkdir -p "${TARGET_DIR}-download"

hf download \
  --repo-type model \
  --local-dir "${TARGET_DIR}-download" \
  --max-workers 1 \
  facebook/sam-3d-objects

mv "${TARGET_DIR}-download/checkpoints" "${TARGET_DIR}"
rm -rf "${TARGET_DIR}-download"

echo "Done. Ensure SAM3D_CHECKPOINT_PATH is set to: ${TARGET_DIR}"

