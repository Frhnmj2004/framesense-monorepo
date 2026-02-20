# SAM 3 Video Inference Service Dockerfile
# Optimized for faster builds with layer caching
# Base image with CUDA 12.6 support
FROM nvidia/cuda:12.6.3-devel-ubuntu22.04 AS base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies in one layer
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3-pip \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3.12 /usr/bin/python \
    && ln -s /usr/bin/python3.12 /usr/bin/python3

# Stage 1: Install PyTorch (cache this layer separately)
FROM base AS pytorch-install
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
# Install PyTorch - this is slow but we cache it
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir torch==2.7.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# Stage 2: Install SAM 3 (cache this separately)
FROM pytorch-install AS sam3-install
WORKDIR /tmp
# Clone and install SAM 3 - cache git clone
RUN --mount=type=cache,target=/root/.cache/pip \
    git clone https://github.com/facebookresearch/sam3.git sam3 && \
    cd sam3 && \
    pip install --no-cache-dir -e . && \
    cd / && \
    rm -rf /tmp/sam3

# Stage 3: Final image with application
FROM sam3-install AS final
WORKDIR /app

# Install application dependencies (cache pip downloads)
COPY requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (this changes most often, so do it last)
COPY . /app/

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
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
