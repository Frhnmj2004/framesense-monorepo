# SAM 3 Video Inference Service

A production-ready FastAPI microservice for GPU-based video segmentation using Meta's SAM 3 (Segment Anything with Concepts) model.

## Features

- **Text-based object detection**: Detect and segment objects in videos using natural language prompts
- **GPU-optimized**: Designed for NVIDIA GPUs (RTX 3090/4090/A4000, minimum 12GB VRAM)
- **Stateless architecture**: No database required, fully stateless service
- **Production-ready**: Error handling, health checks, and proper resource cleanup

## Architecture

The service loads the SAM 3 model once at startup and processes videos through the following pipeline:

1. Download video from URL to temporary storage
2. Initialize SAM 3 session with the video
3. Add text prompt on frame 0
4. Propagate detections through all frames
5. Return structured JSON with bounding boxes and scores
6. Cleanup temporary files and session

## Prerequisites

- **HuggingFace Account**: SAM 3 requires authentication to download checkpoints
  - Request access at: https://huggingface.co/facebook/sam3
  - Generate access token at: https://huggingface.co/settings/tokens
- **NVIDIA GPU**: CUDA 12.6 compatible GPU with minimum 12GB VRAM
- **Docker**: For containerized deployment
- **Docker Compose**: For easy local development (optional but recommended)
- **NVIDIA Container Toolkit**: Required for GPU support in Docker

## Quick Start

The fastest way to get started:

```bash
cd app/inference

# 1. Copy and configure .env file
cp .env.example .env
# Edit .env and add your HF_TOKEN

# 2. Start with docker-compose
docker-compose up -d

# 3. Check health
curl http://localhost:8000/health

# 4. View logs
docker-compose logs -f
```

### Quick smoke test (~1–2 min with 5 frames)

Use `max_frames: 5` to verify the pipeline without a long run:

```powershell
# PowerShell
$body = '{"video_url":"https://res.cloudinary.com/dbujzulsx/video/upload/v1771607112/Cars_Moving_On_Road_Stock_Footage_-_Free_Download_-_Wave_ASMR_Stock_Footage_Riley_Kearl_360p_h264_jiuzxa.mp4","text_prompt":"cars","max_frames":5}'
Invoke-RestMethod -Uri "http://localhost:8000/process-video" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 120
```

```bash
# curl
curl -X POST http://localhost:8000/process-video \
  -H "Content-Type: application/json" \
  -d '{"video_url":"https://res.cloudinary.com/dbujzulsx/video/upload/v1771607112/Cars_Moving_On_Road_Stock_Footage_-_Free_Download_-_Wave_ASMR_Stock_Footage_Riley_Kearl_360p_h264_jiuzxa.mp4","text_prompt":"cars","max_frames":5}'
```

Inference is per-frame; even 5 frames can take ~1–2 minutes. Use `max_frames: 1` or `2` for a faster (~10–30 s) check.

## Local Development

### 1. Set Up Environment

**Option A: Using .env file (Recommended)**

```bash
# Clone the repository
cd app/inference

# Copy the example .env file
cp .env.example .env

# Edit .env and add your HuggingFace token
# HF_TOKEN=your_huggingface_token_here
```

**Option B: Using Environment Variables**

```bash
# Clone the repository
cd app/inference

# Set HuggingFace token (required for model download)
export HF_TOKEN=your_huggingface_token_here

# Optional: Configure other settings
export MODEL_DEVICE=cuda
export MAX_VIDEO_SIZE_MB=500
export VIDEO_DOWNLOAD_TIMEOUT=120
export INFERENCE_TIMEOUT=300
```

The service will automatically load environment variables from a `.env` file in the `app/inference/` directory if it exists. Environment variables set in your shell will override `.env` file values.

### 2. Install Dependencies

**Option A: Using Docker Compose (Recommended for local development)**

```bash
# Enable BuildKit for faster builds (one-time setup)
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Make sure you have a .env file with your HF_TOKEN
cp .env.example .env
# Edit .env and add your HF_TOKEN

# Build and start the service (first build takes 20-30 min, subsequent builds are much faster)
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

**Note:** First build downloads ~2.5GB base image and installs PyTorch/SAM 3 (~20-30 minutes). Subsequent builds with code changes are much faster (~30 seconds - 2 minutes) thanks to layer caching. See `BUILD_OPTIMIZATION.md` for more tips.

**Option B: Using Docker directly**

**Method 1: Pass environment variables directly (Recommended for production)**

```bash
# Build the Docker image
docker build -t sam3-inference .

# Run the container (requires NVIDIA Docker runtime)
# Pass HF_TOKEN as environment variable
docker run --gpus all \
  -p 8000:8000 \
  -e HF_TOKEN=your_huggingface_token_here \
  sam3-inference
```

**Method 2: Use .env file with Docker**

The `.env` file will be automatically loaded if it exists in the build context. However, **it's recommended to pass environment variables directly** for security reasons (don't bake secrets into images).

If you want to use a `.env` file:
```bash
# Build the Docker image (includes .env if present)
docker build -t sam3-inference .

# Run the container
docker run --gpus all \
  -p 8000:8000 \
  sam3-inference
```

**Note:** Environment variables passed with `-e` will override `.env` file values.

**Option B: Local Python Installation**

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install PyTorch with CUDA 12.6
pip install torch==2.7.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# Clone and install SAM 3
git clone https://github.com/facebookresearch/sam3.git /tmp/sam3
cd /tmp/sam3
pip install -e .
cd -

# Install application dependencies
pip install -r requirements.txt
```

### 3. Run the Service

```bash
# Using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000

# Or using Python
python main.py
```

The service will be available at `http://localhost:8000`

### 4. Test the Service

```bash
# Health check
curl http://localhost:8000/health

# Process a video
curl -X POST http://localhost:8000/process-video \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "text_prompt": "yellow van"
  }'
```

## API Endpoints

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

### `POST /process-video`

Process a video with SAM 3 text prompt.

**Request:**
```json
{
  "video_url": "https://example.com/video.mp4",
  "text_prompt": "yellow van"
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "frames_processed": 120,
  "detections": [
    {
      "frame_index": 0,
      "boxes": [[100, 200, 300, 400], [500, 600, 700, 800]],
      "scores": [0.98, 0.95],
      "mask_shape": [1080, 1920]
    },
    {
      "frame_index": 1,
      "boxes": [[105, 205, 305, 405]],
      "scores": [0.97],
      "mask_shape": [1080, 1920]
    }
  ]
}
```

**Error Responses:**
- `400`: Invalid request (empty prompt, etc.)
- `422`: Validation error (invalid URL format, etc.)
- `502`: Video download failure
- `500`: Model inference error
- `503`: Service not initialized

## RunPod Pod Deployment (Step-by-Step)

Use this when your **backend and frontend are on Railway** and only the **GPU inference** runs on RunPod. The Railway backend will call the RunPod inference URL.

**Architecture:** `Frontend (Railway) → Backend (Railway) → Inference (RunPod, this service)`

### Step 1: From RunPod Console Home

1. In the left sidebar, click **Manage → Pods**.
2. Click **+ Deploy** or **+ New Pod**.

### Step 2: Choose a GPU (Demo Phase)

- **Recommended for demo (good speed, low cost):** **RTX 3090** (24 GB) — ~\$0.44/hr. About **5–7× faster** than a 6 GB laptop GPU.
- **Faster option:** **RTX 4090** (~\$0.74/hr) or **A10G** (~\$0.76/hr) — ~10–15× faster.
- **Avoid:** GPUs with &lt;12 GB VRAM (SAM 3 needs headroom; 6 GB was your limit locally).

Select **Pod** (not Serverless). Pick a template with **Ubuntu 22.04** and one of the GPUs above.

### Step 3: Configure the Pod

- **Container Image:** Leave blank if you will build from your repo (see Step 5). Or use a pre-built image if you push to a registry.
- **Expose HTTP Ports:** Add **8000** (so RunPod gives you a public URL like `https://xxxx-8000.proxy.runpod.net`).
- **Volume (optional but recommended):** Add a volume and mount it at **/root/.cache/huggingface** so the SAM 3 checkpoint is cached across restarts.
- **Secrets / Environment variables:** Add these (use RunPod **Secrets** for `HF_TOKEN` so it’s not visible in the UI):
  - `HF_TOKEN` — your HuggingFace token (required for SAM 3).
  - `MODEL_DEVICE=cuda`
  - `DEFAULT_MAX_FRAMES=300` — default cap when the client doesn’t send `max_frames` (300 is tuned for A40/24GB+; use `0` for no cap).
  - `MAX_VIDEO_SIZE_MB=500`
  - `VIDEO_DOWNLOAD_TIMEOUT=120`
  - `INFERENCE_TIMEOUT=300`

### Step 4: Deploy and Wait

- Click **Deploy** and wait for the Pod to be **Running**.
- Note the **Pod ID** and the **Public URL** for port 8000 (e.g. `https://xxxx-8000.proxy.runpod.net`). This is your **inference base URL**.

### Step 5: Build and Run the Inference Service on the Pod

1. Click the Pod → **Connect** → **Start Web Terminal** (or use SSH if you prefer).
2. In the terminal:
   ```bash
   git clone https://github.com/YOUR_ORG/framesense-monorepo.git
   cd framesense-monorepo/app/inference
   ```
3. Set env vars (or use RunPod Secrets so they’re already in the environment):
   ```bash
   export HF_TOKEN=your_huggingface_token
   export DEFAULT_MAX_FRAMES=300
   ```
4. Build and run with Docker:
   ```bash
   docker build -t sam3-inference .
   docker run --gpus all -d --name sam3-inference -p 8000:8000 \
     -e HF_TOKEN -e DEFAULT_MAX_FRAMES=300 \
     -v /root/.cache/huggingface:/root/.cache/huggingface \
     sam3-inference
   ```
5. Wait **5–10 minutes** for the model to load (first time). Then:
   ```bash
   curl https://YOUR_POD_ID-8000.proxy.runpod.net/health
   ```
   You should get `{"status":"ok"}`.

### Step 6: Connect Railway Backend to RunPod

In your **Railway** backend service:

1. Add an environment variable, e.g. **`INFERENCE_URL`** = `https://YOUR_POD_ID-8000.proxy.runpod.net` (no trailing slash).
2. In your backend code, call the inference service at:
   - `POST {INFERENCE_URL}/process-video`
   - Body: `{ "video_url": "...", "text_prompt": "...", "max_frames": 300 }` (omit `max_frames` to use RunPod’s `DEFAULT_MAX_FRAMES`).

That’s it. Frontend and API live on Railway; heavy GPU work runs on RunPod.

### Environment Variables Reference (RunPod / .env)

| Variable | Default | Description |
|----------|---------|-------------|
| `HF_TOKEN` | — | **Required.** HuggingFace token for SAM 3. |
| `MODEL_DEVICE` | `cuda` | `cuda` or `cpu`. |
| `DEFAULT_MAX_FRAMES` | `300` | Default max frames when client omits `max_frames` (300 for A40/24GB+; use `0` for no cap). |
| `MAX_VIDEO_SIZE_MB` | `500` | Max video download size (MB). |
| `VIDEO_DOWNLOAD_TIMEOUT` | `120` | Download timeout (seconds). |
| `INFERENCE_TIMEOUT` | `300` | Request timeout (seconds). |
| `HOST` | `0.0.0.0` | Bind host. |
| `PORT` | `8000` | Bind port. |

Frame limit: it’s controlled by **env** `DEFAULT_MAX_FRAMES` (server default) and/or by the **request** body field **`max_frames`** (per request). Both are already supported; no code change needed.

**Option B: Use RunPod Template**

1. Create a custom template with the Dockerfile
2. Set environment variables in RunPod UI
3. Deploy directly from template

### 4. Verify Deployment

```bash
# Check health endpoint
curl http://<pod-ip>:8000/health

# Test video processing
curl -X POST http://<pod-ip>:8000/process-video \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "text_prompt": "yellow van"
  }'
```

### 5. Monitor Logs

```bash
# View container logs
docker logs -f sam3-inference

# Check GPU usage
nvidia-smi
```

## Configuration

All configuration is done via environment variables. You can set them in two ways:

1. **Using a `.env` file** (recommended for local development):
   - Copy `.env.example` to `.env`
   - Edit `.env` with your values
   - The service automatically loads variables from `.env` on startup

2. **Using environment variables** (recommended for production):
   - Set environment variables directly
   - Environment variables override `.env` file values

| Variable | Default | Description |
|----------|---------|-------------|
| `HF_TOKEN` | None | HuggingFace access token (required) |
| `MODEL_DEVICE` | `cuda` | Device for inference (`cuda` or `cpu`) |
| `MAX_VIDEO_SIZE_MB` | `500` | Maximum video file size in MB |
| `VIDEO_DOWNLOAD_TIMEOUT` | `120` | Video download timeout in seconds |
| `INFERENCE_TIMEOUT` | `300` | Maximum inference time per request |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |

## Performance Considerations

- **Model Loading**: First startup takes 2-5 minutes to download and load the SAM 3 checkpoint (~4GB)
- **Memory Usage**: Model requires ~4-6GB VRAM. Additional VRAM needed for video processing
- **Processing Speed**: Depends on video length and resolution. Typical: 1-5 seconds per frame on RTX 3090
- **Concurrent Requests**: Service processes one request at a time (single worker) to optimize GPU memory usage

## Troubleshooting

### Model fails to load

- Verify `HF_TOKEN` is set correctly
- Check HuggingFace access: https://huggingface.co/facebook/sam3
- Ensure sufficient disk space (~10GB for model cache)

### CUDA out of memory

- Reduce video resolution or length
- Ensure no other processes are using GPU
- Check available VRAM: `nvidia-smi`

### Video download fails

- Verify video URL is accessible
- Check network connectivity
- Increase `VIDEO_DOWNLOAD_TIMEOUT` if needed
- Ensure video size is within `MAX_VIDEO_SIZE_MB` limit

### BFloat16 / float dtype mismatch (`Input type (c10::BFloat16) and bias type (float) should be the same`)

This error occurs when the model weights are in float32 but SAM 3 internally casts backbone features to bfloat16 (hardcoded in `sam3/model/sam3_image.py`). The service automatically converts the model to bfloat16 on startup when running on a CUDA GPU that supports bf16, so you should not see this error. If you do:

- Verify your GPU supports bfloat16 (`torch.cuda.is_bf16_supported()` should return `True`). All Ampere (A100, A40, RTX 3090) and newer GPUs support it.
- If your GPU does NOT support bfloat16 (e.g. Volta V100), you will need to patch SAM 3 source code to remove the explicit `.to(torch.bfloat16)` cast.

### Empty detections returned

- Verify text prompt is descriptive and matches objects in video
- Check video quality and resolution
- Try different text prompts (SAM 3 supports open vocabulary)

## License

This service uses SAM 3, which is licensed under the SAM License. See:
- SAM 3 License: https://github.com/facebookresearch/sam3/blob/main/LICENSE
- SAM 3 Repository: https://github.com/facebookresearch/sam3
