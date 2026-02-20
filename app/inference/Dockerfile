# SAM 3 Video Inference Service Dockerfile
# Base image with CUDA 12.6 support
FROM nvidia/cuda:12.6.3-devel-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3-pip \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python
RUN ln -s /usr/bin/python3.12 /usr/bin/python && \
    ln -s /usr/bin/python3.12 /usr/bin/python3

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Install PyTorch 2.7.0 with CUDA 12.6 support
# Using the official PyTorch CUDA index for CUDA 12.6
RUN pip install torch==2.7.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# Verify PyTorch CUDA installation
RUN python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')"

# Clone and install SAM 3 from source
# SAM 3 requires authentication to download checkpoints (set HF_TOKEN env var)
WORKDIR /app
RUN git clone https://github.com/facebookresearch/sam3.git /tmp/sam3 && \
    cd /tmp/sam3 && \
    pip install -e . && \
    cd /app && \
    rm -rf /tmp/sam3

# Install application dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Copy application code
COPY . /app/

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 8000

# Health check (optional, can be used by orchestrators)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
# Use uvicorn with single worker for GPU inference
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# RunPod Deployment Notes:
# =======================
# 1. Use RunPod Pod (not serverless) with NVIDIA GPU template
# 2. Recommended GPU: RTX 3090 / 4090 / A4000 (minimum 12GB VRAM)
# 3. Mount persistent volume for HuggingFace cache:
#    - Mount point: /root/.cache/huggingface
#    - This speeds up subsequent model loads
# 4. Set environment variables:
#    - HF_TOKEN: Your HuggingFace access token (required for SAM 3 checkpoint download)
#    - MODEL_DEVICE: "cuda" (default) or "cpu"
#    - MAX_VIDEO_SIZE_MB: Maximum video size in MB (default: 500)
#    - VIDEO_DOWNLOAD_TIMEOUT: Download timeout in seconds (default: 120)
#    - INFERENCE_TIMEOUT: Inference timeout per request (default: 300)
# 5. Expose port 8000 in RunPod pod settings
# 6. After deployment, test with: curl http://<pod-ip>:8000/health
