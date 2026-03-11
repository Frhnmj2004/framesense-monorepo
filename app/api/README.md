# Framesense API (NestJS)

Backend for video upload to S3, metadata storage in PostgreSQL, and orchestration of the Python inference service (SAM 3 segmentation).

## Features

- **POST /videos** — Upload video (multipart), store in S3 and DB, return presigned GET URL
- **GET /videos/:id** — Get video metadata and latest segmentation result
- **POST /segment** — Request segmentation (sync or async); calls Python `POST /process-video`
- **GET /jobs/:id** — Get job status and result
- **POST /inference/callback** — Webhook for async inference result (optional)
- **GET /health** — Health check

## Prerequisites

- Node.js 20+
- PostgreSQL 15+
- AWS credentials and S3 bucket (or LocalStack)
- Python inference service running (see `app/inference`)

## Project setup

### Nest CLI (used to generate modules)

```bash
npm i -g @nestjs/cli
cd app/api
nest g module videos
nest g controller videos --no-spec
nest g service videos --no-spec
nest g module inference
nest g controller inference --no-spec
nest g service inference --no-spec
nest g module db
nest g service db --no-spec
nest g module common
```

### Install and configure

```bash
cd app/api
npm install
cp .env.example .env
# Edit .env: DATABASE_URL, AWS_*, S3_BUCKET, INFERENCE_URL
```

### Migrations

Migrations run automatically on app startup. SQL files live in `migrations/` and are applied in order via `MigrationRunnerService`. Prisma is used for queries only; schema is kept in sync with:

```bash
npm run sync:prisma
```

### Run locally

```bash
# Ensure Postgres is running and DATABASE_URL is set
npm run start:dev
```

Server listens on `PORT` (default 3000).

## Docker

From repo root (or `deployments/docker`):

```bash
cd deployments/docker
cp .env.example .env
# Set AWS_*, S3_BUCKET, INFERENCE_URL, etc.
docker compose up --build -d
```

API: `http://localhost:3000`. Postgres and inference services are defined in the same compose file.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| PORT | 3000 | Server port |
| DATABASE_URL | — | PostgreSQL connection string |
| AWS_REGION | us-east-1 | AWS region |
| AWS_ACCESS_KEY_ID | — | AWS access key |
| AWS_SECRET_ACCESS_KEY | — | AWS secret key |
| S3_BUCKET | — | S3 bucket name |
| S3_UPLOAD_MAX_BYTES | 1073741824 | Max upload size (1GB) |
| INFERENCE_URL | http://localhost:8000 | Python inference base URL |
| INFERENCE_TIMEOUT_MS | 900000 | Inference request timeout (15 min) |
| JWT_SECRET | changeme | TODO: auth |
| MIGRATION_TABLE_NAME | schema_migrations | Migrations table |
| PRESIGNED_URL_EXPIRES_SEC | 3600 | Presigned URL TTL (playback) |
| BACKEND_URL | http://localhost:3000 | Used for callback URL in async mode |

## API examples

### Health

```bash
curl http://localhost:3000/health
# {"status":"ok"}
```

### Upload video

```bash
curl -X POST http://localhost:3000/videos \
  -F "file=@/path/to/video.mp4" \
  -F "title=My video"
# {"success":true,"data":{"id":"...","title":"My video","s3_key":"videos/2025/02/...","presigned_url":"...","uploaded_at":"..."}}
```

### Request segmentation (sync)

```bash
curl -X POST http://localhost:3000/segment \
  -H "Content-Type: application/json" \
  -d '{"videoId":"<uuid-from-upload>","prompt":"cars","mode":"sync","config":{"max_frame_count":50}}'
# {"success":true,"data":{"job_id":"...","result":{...}}}
```

### Get job

```bash
curl http://localhost:3000/jobs/<job_id>
# {"success":true,"data":{"job_id":"...","status":"completed","result_json":{...}}}
```

### Python inference response (stored as result_json)

The Python service returns JSON in this shape (validated and stored as-is):

```json
{
  "session_id": "uuid",
  "frames_processed": 5,
  "video_width": 640,
  "video_height": 360,
  "detections": [
    {
      "frame_index": 0,
      "objects": [
        {
          "object_id": 0,
          "score": 0.94,
          "box": [354, 129, 455, 261],
          "mask_rle": { "counts": "127617 7 329 ...", "size": [360, 640] }
        }
      ]
    }
  ]
}
```

## Tests

```bash
# Unit
npm run test

# E2E (requires Postgres and optionally INFERENCE_URL + S3 for full flow)
npm run test:e2e
```

E2E tests expect `DATABASE_URL` to be set. For POST /videos and POST /segment e2e, configure S3 and inference service as needed.

## TODOs (production hardening)

- JWT auth for protected endpoints
- Rate limiting
- Metrics (e.g. Prometheus)
- HMAC verification for POST /inference/callback
