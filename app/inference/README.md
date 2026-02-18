# Video Annotation Platform - Inference Service

Enterprise-grade Python inference microservice for SAM 3 (Segment Anything Model 3) segmentation.

## Features

- **SAM 3 Integration**: Text-prompted and automatic image/video segmentation
- **REST API**: Synchronous image segmentation endpoint
- **Redis Job Queue**: Async video processing with idempotency
- **S3 Integration**: Download videos and upload mask results
- **GPU Support**: CUDA acceleration with fail-fast validation
- **Prometheus Metrics**: Request/job/frame counters
- **Structured Logging**: JSON-formatted logs
- **Graceful Shutdown**: Handles SIGTERM/SIGINT properly

## Architecture

```
Go Backend → POST /v1/segment (sync image segmentation)
Go Backend → Redis Queue → Worker (async video processing)
```

**TODO: GRPC** - REST endpoints marked for future gRPC migration in Phase 2.

## Prerequisites

- Python 3.10+
- CUDA-capable GPU (optional, set `REQUIRE_GPU=false` for CPU)
- Redis server
- AWS S3 access (or S3-compatible storage)

## Local Development

### With GPU

1. **Install dependencies:**

```bash
cd app/inference
pip install -r requirements.txt
```

2. **Set environment variables:**

```bash
export MODEL_PATH=facebook/sam3
export REQUIRE_GPU=true
export INFERENCE_PORT=8000
export MAX_CONCURRENCY=2
export INFERENCE_TIMEOUT=30
export SAMPLE_FPS=1.0

# S3 Configuration
export S3_REGION=us-east-1
export S3_BUCKET=your-bucket-name
export S3_ACCESS_KEY_ID=your-access-key
export S3_SECRET_ACCESS_KEY=your-secret-key

# Redis Configuration
export REDIS_URL=redis://localhost:6379/0
export REDIS_JOB_QUEUE=inference:jobs

export ENVIRONMENT=development
```

3. **Start Redis:**

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

4. **Run the API server:**

```bash
python cmd/server/main.py
```

The API will be available at `http://localhost:8000`

### Without GPU (CPU Mode)

Set `REQUIRE_GPU=false`:

```bash
export REQUIRE_GPU=false
python cmd/server/main.py
```

**Note:** CPU mode is significantly slower and intended for development/testing only.

## Running Redis Consumer (Worker)

The Redis consumer processes async video jobs. Run it in a separate process:

```bash
python -m workers.redis_consumer
```

Or integrate it into your main process (see `cmd/server/main.py` for example).

## Docker

### Build and Run

```bash
cd app/inference
docker build -t framesense-inference .
docker run --gpus all -p 8000:8000 \
  -e MODEL_PATH=facebook/sam3 \
  -e S3_BUCKET=your-bucket \
  -e S3_ACCESS_KEY_ID=your-key \
  -e S3_SECRET_ACCESS_KEY=your-secret \
  framesense-inference
```

### Docker Compose

From the repository root:

```bash
docker-compose up inference redis
```

This starts both the inference service and Redis.

## API Endpoints

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok"
}
```

### Segment Image

```bash
curl -X POST http://localhost:8000/v1/segment \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "<base64_encoded_image>",
    "prompt": "person"
  }'
```

Response:
```json
{
  "success": true,
  "masks": [
    {
      "rle": "encoded_mask_string",
      "bbox": [10, 20, 100, 200],
      "score": 0.95
    }
  ]
}
```

### Metrics (Prometheus)

```bash
curl http://localhost:8000/metrics
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `facebook/sam3` | HuggingFace model ID or local path |
| `INFERENCE_PORT` | `8000` | HTTP server port |
| `REQUIRE_GPU` | `true` | Fail-fast if CUDA unavailable |
| `MAX_CONCURRENCY` | `2` | Max parallel inference calls |
| `INFERENCE_TIMEOUT` | `30` | Per-request timeout (seconds) |
| `SAMPLE_FPS` | `1.0` | Frames per second for video extraction |
| `S3_REGION` | `us-east-1` | AWS region |
| `S3_BUCKET` | - | S3 bucket name (required) |
| `S3_ACCESS_KEY_ID` | - | AWS access key |
| `S3_SECRET_ACCESS_KEY` | - | AWS secret key |
| `S3_ENDPOINT` | - | S3-compatible endpoint (optional) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `REDIS_JOB_QUEUE` | `inference:jobs` | Redis queue name |
| `ENVIRONMENT` | `development` | Environment name |

## Redis Job Format

Jobs are pushed to Redis as JSON:

```json
{
  "job_id": "unique-job-id",
  "s3_key": "videos/input.mp4",
  "callback_url": "http://go-backend:8080/api/jobs/callback"
}
```

The worker:
1. Downloads video from S3
2. Extracts frames at configured FPS
3. Runs SAM 3 segmentation on each frame
4. Uploads mask results to S3 (`results/{job_id}/masks.json`)
5. POSTs status to `callback_url`

## Idempotency

Jobs are idempotent: if a job with the same `job_id` is already processing or completed, it will be skipped. This is implemented using Redis `SET job:{job_id}:status processing NX`.

## Testing

Run tests:

```bash
pip install pytest
pytest tests/
```

## Project Structure

```
app/inference/
├── cmd/server/main.py      # Entry point
├── app/
│   ├── config.py           # Configuration (Pydantic)
│   └── container.py        # DI container
├── core/
│   ├── model_loader.py     # SAM 3 model loading
│   ├── predictor.py         # Inference with concurrency/timeout
│   └── jobs.py              # Video job processing
├── api/
│   ├── routes.py            # FastAPI routes
│   └── schemas.py           # Pydantic schemas
├── infra/
│   ├── logging.py           # JSON logger
│   └── exceptions.py        # Custom exceptions
├── workers/
│   └── redis_consumer.py    # Redis job consumer
├── tests/                   # Unit tests
├── requirements.txt         # Dependencies
└── Dockerfile               # Docker build
```

## Security Notes

**TODO: AUTH** - Auth middleware stub exists but doesn't validate tokens in Phase 1. Implement token validation in Phase 2.

## Troubleshooting

### CUDA Not Available

If you see "CUDA is not available", either:
- Set `REQUIRE_GPU=false` for CPU mode
- Ensure NVIDIA drivers and CUDA are installed
- Check GPU availability: `nvidia-smi`

### Model Download Fails

The model is downloaded from HuggingFace on first run. Ensure:
- Internet connection is available
- HuggingFace token is set (if model is gated): `export HF_TOKEN=your-token`

### Redis Connection Errors

Ensure Redis is running:
```bash
redis-cli ping
```

Should return `PONG`.

## Next Steps (Phase 2+)

- gRPC migration (marked with `TODO: GRPC`)
- Token-based authentication (`TODO: AUTH`)
- Advanced job orchestration
- Multi-GPU support
- Model versioning

## License

Apache 2.0
