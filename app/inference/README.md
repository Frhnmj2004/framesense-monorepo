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

**Option A: Using Docker (Recommended)**

```bash
# Build the Docker image
docker build -t sam3-inference .

# Run the container (requires NVIDIA Docker runtime)
docker run --gpus all \
  -p 8000:8000 \
  -e HF_TOKEN=your_huggingface_token_here \
  sam3-inference
```

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

## RunPod Pod Deployment

### 1. Create RunPod Pod

1. Go to [RunPod](https://www.runpod.io/) and create a new Pod
2. Select **Pod** (not Serverless) with NVIDIA GPU template
3. Recommended GPU: RTX 3090 / 4090 / A4000 (minimum 12GB VRAM)
4. Choose Ubuntu 22.04 base image

### 2. Configure Pod Settings

**Environment Variables:**
```
HF_TOKEN=your_huggingface_token_here
MODEL_DEVICE=cuda
MAX_VIDEO_SIZE_MB=500
VIDEO_DOWNLOAD_TIMEOUT=120
INFERENCE_TIMEOUT=300
```

**Port Mapping:**
- Container Port: `8000`
- Public Port: `8000` (or your preferred port)

**Volume Mounts (Optional but Recommended):**
- Mount point: `/root/.cache/huggingface`
- This caches SAM 3 checkpoints for faster subsequent loads

### 3. Build and Deploy

**Option A: Build from Dockerfile**

```bash
# SSH into your RunPod pod
# Clone your repository
git clone <your-repo-url>
cd framesense-monorepo/app/inference

# Build Docker image
docker build -t sam3-inference .

# Run container
docker run --gpus all \
  -d \
  --name sam3-inference \
  -p 8000:8000 \
  -e HF_TOKEN=$HF_TOKEN \
  -v /root/.cache/huggingface:/root/.cache/huggingface \
  sam3-inference
```

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

### Empty detections returned

- Verify text prompt is descriptive and matches objects in video
- Check video quality and resolution
- Try different text prompts (SAM 3 supports open vocabulary)

## License

This service uses SAM 3, which is licensed under the SAM License. See:
- SAM 3 License: https://github.com/facebookresearch/sam3/blob/main/LICENSE
- SAM 3 Repository: https://github.com/facebookresearch/sam3
