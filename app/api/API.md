# Framesense NestJS API — Reference for Frontend

This document describes the NestJS backend API for the Framesense application. Use it as the single source of truth for request/response shapes, error handling, and recommended flows when building the frontend.

---

## Table of contents

1. [Overview](#1-overview)
2. [Base URL & environment](#2-base-url--environment)
3. [Conventions](#3-conventions)
4. [Endpoints](#4-endpoints)
5. [Data types (shared)](#5-data-types-shared)
6. [Recommended flows](#6-recommended-flows)
7. [Error handling](#7-error-handling)

---

## 1. Overview

The API provides:

- **Video upload and metadata**: upload MP4 to S3, store metadata in DB, get presigned playback URLs.
- **Segmentation jobs**: start a video segmentation job (sync or async), poll job status, and retrieve detection results.

There is **no authentication** on these endpoints in the current implementation. All endpoints return JSON. Upload uses `multipart/form-data`.

---

## 2. Base URL & environment

- **Base URL**: Use the backend root (e.g. `http://localhost:3000` in development). Configurable via `PORT` (default `3000`) and your deployment host.
- **Recommended**: Read base URL from env (e.g. `VITE_API_URL` or `NEXT_PUBLIC_API_URL`) so you can switch between local and deployed backends.

Example:

```text
Base: http://localhost:3000
GET  http://localhost:3000/health
POST http://localhost:3000/videos
GET  http://localhost:3000/videos/:id
POST http://localhost:3000/segment
GET  http://localhost:3000/jobs/:id
POST http://localhost:3000/inference/callback
```

---

## 3. Conventions

### Response envelope

Successful responses use a common envelope:

```json
{
  "success": true,
  "data": { ... }
}
```

- `success`: always `true` for HTTP 2xx.
- `data`: payload (shape depends on endpoint). Omitted for some endpoints (e.g. callback).

### Errors

Errors use standard HTTP status codes and a body that may include a `message` (and sometimes validation details). See [Error handling](#7-error-handling).

### IDs

- **Video ID** and **Job ID** are UUIDs (e.g. `c0845ffd-d927-41ce-a06f-3591304d72f0`). Use them as path parameters as-is; validation returns `400` if the format is invalid.

---

## 4. Endpoints

### 4.1 Root & health

#### `GET /`

**Description:** Simple root response (string).

**Response (200):** Plain text string (e.g. `"Hello World!"`). Not JSON.

**Frontend use:** Optional; prefer `GET /health` for “backend up” checks.

---

#### `GET /health`

**Description:** Liveness/health check. No side effects.

**Response (200):**

```json
{
  "status": "ok"
}
```

**Frontend use:** Use for “is the API reachable?” before starting upload or segmentation flows.

---

### 4.2 Videos

#### `POST /videos`

**Description:** Upload a video file (MP4). The file is stored in S3 and metadata in the database. Response includes a **presigned URL** for temporary direct playback/download (no auth needed for that URL until it expires).

**Content-Type:** `multipart/form-data`

**Request body (form fields):**

| Field   | Type   | Required | Description                                      |
|--------|--------|----------|--------------------------------------------------|
| `file` | File   | Yes      | MP4 video file (binary).                         |
| `title`| string | No       | Optional title; max 500 characters.              |

**Validation:**

- `file` missing → `400` with message `"file is required"`.
- File size &gt; server limit (default 1 GB) → `400` with message describing max size.
- File type not allowed (non-MP4 / wrong MIME) → `400` with message `"Invalid file type. Only MP4 video is accepted."`.
- S3/configuration errors → `403` or `503` as in [Error handling](#7-error-handling).

**Response (201 implied by success):**

```json
{
  "success": true,
  "data": {
    "id": "c0845ffd-d927-41ce-a06f-3591304d72f0",
    "title": "Cars moving",
    "s3_key": "videos/2026/03/c0845ffd-d927-41ce-a06f-3591304d72f0.mp4",
    "presigned_url": "https://framesense-storage.s3.ap-south-1.amazonaws.com/videos/2026/03/...?X-Amz-...",
    "uploaded_at": "2026-03-12T07:45:15.023Z"
  }
}
```

| Field           | Type   | Description |
|----------------|--------|-------------|
| `id`           | string | UUID of the video; use for `GET /videos/:id` and `POST /segment` `videoId`. |
| `title`        | string \| null | Title if provided. |
| `s3_key`       | string | Internal storage key (for debugging; frontend usually only needs `presigned_url`). |
| `presigned_url`| string | Temporary URL to play or download the video; expires after a configured time (e.g. 1 hour). |
| `uploaded_at`  | string | ISO 8601 timestamp of upload. |

**Frontend use:** After a successful upload, store `data.id` and optionally `data.presigned_url` for immediate playback. Use `data.id` when starting a segmentation job.

---

#### `GET /videos/:id`

**Description:** Fetch a video’s metadata and, if available, the **latest completed** segmentation result for that video.

**Path parameters:**

| Name | Type   | Description |
|------|--------|-------------|
| `id` | string | Video UUID. Must be a valid UUID. |

**Response (200):**

```json
{
  "success": true,
  "data": {
    "id": "c0845ffd-d927-41ce-a06f-3591304d72f0",
    "title": "Cars moving",
    "s3_key": "videos/2026/03/c0845ffd-d927-41ce-a06f-3591304d72f0.mp4",
    "status": "uploaded",
    "metadata": null,
    "created_at": "2026-03-12T07:45:15.023Z",
    "updated_at": "2026-03-12T07:45:15.023Z",
    "result_json": { ... }
  }
}
```

If there is no completed job for this video, `result_json` is omitted (or `undefined`). If there is one, `result_json` has the same shape as the [segmentation result](#segmentation-result-object) below.

**Errors:**

- Invalid UUID → `400`.
- Video not found → `404` with message `"Video not found: <id>"`.

**Frontend use:** To show “video + latest result” in one call (e.g. detail page), use `GET /videos/:id`. For playback, you still need a presigned URL: either from the initial upload response or from a separate presigning endpoint if you add one later.

---

### 4.3 Segmentation (inference) and jobs

#### `POST /segment`

**Description:** Start a segmentation job for a given video and text prompt. Two modes:

- **`sync`**: The HTTP request blocks until the inference service finishes (can be 1–2 minutes). Response includes the full result.
- **`async`**: The server returns immediately with a `job_id` and status `queued`. You must poll `GET /jobs/:id` until status is `completed` or `failed`.

**Content-Type:** `application/json`

**Request body:**

```json
{
  "videoId": "c0845ffd-d927-41ce-a06f-3591304d72f0",
  "prompt": "white car",
  "mode": "sync",
  "config": {
    "max_frame_count": 300,
    "sample_fps": null
  }
}
```

| Field     | Type   | Required | Description |
|----------|--------|----------|-------------|
| `videoId`| string | Yes      | UUID of an existing video (from `POST /videos`). |
| `prompt` | string | Yes      | Text prompt for segmentation (e.g. “white car”); min length 1. |
| `mode`  | string | Yes      | `"sync"` or `"async"`. |
| `config`| object | No       | Optional; see below. |

**`config` (optional):**

| Field             | Type   | Description |
|-------------------|--------|-------------|
| `max_frame_count` | number | Cap on frames processed (e.g. 300). Omit or 0 to use inference default. |
| `sample_fps`      | number | Reserved for future use. |

**Validation:**

- Invalid UUID for `videoId` → `400`.
- Empty or missing `prompt` → `400`.
- `mode` not `"sync"` or `"async"` → `400`.
- Video not found → `404` (from service when resolving video for presigned URL).

**Response — sync mode (200):**

```json
{
  "success": true,
  "data": {
    "job_id": "53c0020c-1821-4321-8c68-6116307ebc65",
    "result": {
      "session_id": "0c2e9fcf-958b-4ece-a4bf-7529d5eee7ae",
      "frames_processed": 300,
      "video_width": 640,
      "video_height": 360,
      "detections": [ ... ]
    }
  }
}
```

**Response — async mode (200):**

```json
{
  "success": true,
  "data": {
    "job_id": "370f81fc-3fdd-4ed7-a963-e013d6469194",
    "status": "queued"
  }
}
```

In async mode, the backend runs the inference in the background. Poll `GET /jobs/:id` with `data.job_id` until `status` is `completed` or `failed`. Inference often takes **1–2 minutes**; poll every 5–10 seconds.

**Errors:**

- Inference service unreachable or timeout → `503` with message like `"Inference service failed: ..."`.
- Invalid inference response (validation) → `400` with message `"Invalid inference response: ..."`.

**Frontend use:** Prefer **async** in the UI so the request doesn’t block; show a “Processing…” state and poll `GET /jobs/:id`. Use **sync** only if you need a single request/response (e.g. server-side or small clips).

---

#### `GET /jobs/:id`

**Description:** Get the current status and result of a segmentation job. Use this to poll after `POST /segment` with `mode: "async"`.

**Path parameters:**

| Name | Type   | Description |
|------|--------|-------------|
| `id` | string | Job UUID returned from `POST /segment` (`data.job_id`). |

**Response (200):**

```json
{
  "success": true,
  "data": {
    "job_id": "370f81fc-3fdd-4ed7-a963-e013d6469194",
    "video_id": "c0845ffd-d927-41ce-a06f-3591304d72f0",
    "prompt": "white car",
    "status": "completed",
    "result_json": { ... },
    "created_at": "2026-03-12T07:45:19.802Z",
    "updated_at": "2026-03-12T07:46:22.123Z"
  }
}
```

| Field        | Type   | Description |
|-------------|--------|-------------|
| `job_id`    | string | Same as path `id`. |
| `video_id`  | string | Video UUID this job belongs to. |
| `prompt`    | string | Prompt used for this job. |
| `status`    | string | `"queued"` \| `"completed"` \| `"failed"`. |
| `result_json` | object \| null | Present when `status === "completed"`; same shape as [segmentation result](#segmentation-result-object). `null` when queued or failed. |
| `created_at`  | string | ISO 8601. |
| `updated_at`  | string | ISO 8601. |

**Errors:**

- Invalid UUID → `400`.
- Job not found → `404` with message `"Job not found: <id>"`.

**Frontend use:** Poll until `data.status` is `completed` or `failed`. On `completed`, use `data.result_json` for visualizations; on `failed`, show an error (no result payload).

---

#### `POST /inference/callback`

**Description:** Webhook endpoint for an **external** inference service to push results back to the backend (alternative to the backend calling the inference service and waiting). Not used by the default in-process flow. The backend expects a valid inference result body and updates the job to `completed` (or errors).

**Typical caller:** External inference worker (e.g. Python service in another process) that was given a `job_id` and a callback URL.

**Query or body:**

- `job_id` (required): either query parameter `?job_id=<uuid>` or inside JSON body as `job_id`.
- Body: full inference result object (same shape as [segmentation result](#segmentation-result-object)).

**Response (200):**

```json
{
  "success": true
}
```

**Errors:**

- Missing or invalid `job_id` → `400` with message `"job_id is required in query or body"`.
- Invalid result shape → `400` (validation).

**Frontend use:** Frontend does not call this; it is for server-to-server integration.

---

## 5. Data types (shared)

### Segmentation result object

Returned inside `result` (sync) or `result_json` (job / video):

```ts
{
  session_id: string;        // Inference session id
  frames_processed: number;
  video_width: number;
  video_height: number;
  detections: Array<{
    frame_index: number;
    objects: Array<{
      object_id: number;
      score: number;
      box: [number, number, number, number];  // [x1, y1, x2, y2] or similar
      mask_rle: {
        counts: string;     // RLE-encoded mask
        size: [number, number];
      };
    }>;
  }>;
}
```

- **`detections`**: One entry per frame (or for frames that have detections). `frame_index` is 0-based.
- **`objects`**: Per-frame detections (bounding box, score, optional RLE mask). Use `box` for drawing rectangles; use `mask_rle` for pixel-accurate masks if your UI supports RLE decoding.

---

## 6. Recommended flows

### Flow A: Upload → play (no segmentation)

1. `POST /videos` with `file` (+ optional `title`).
2. Use `data.presigned_url` to play the video (e.g. in `<video src="...">`). Optionally store `data.id` for later segmentation.

### Flow B: Upload → segment (async) → show result

1. `POST /videos` with `file` (+ optional `title`). Store `data.id`.
2. `POST /segment` with `{ videoId: data.id, prompt: "white car", mode: "async" }`. Store `data.job_id`.
3. Poll `GET /jobs/:id` (e.g. every 5–10 s) until `data.status` is `completed` or `failed`.
4. If `completed`, use `data.result_json` (e.g. draw boxes or masks per frame). If `failed`, show error.
5. Optional: `GET /videos/:id` to get video metadata plus latest `result_json` in one call.

### Flow C: Segment existing video (async)

1. Ensure you have a video ID (e.g. from a list or `GET /videos/:id`).
2. `POST /segment` with `{ videoId, prompt, mode: "async" }`. Store `data.job_id`.
3. Poll `GET /jobs/:id` until `status` is `completed` or `failed`.
4. Use `result_json` or show error as in Flow B.

### Flow D: Segment and wait in one request (sync)

1. Have a video ID.
2. `POST /segment` with `{ videoId, prompt, mode: "sync" }`. Request may take 1–2 minutes.
3. On success, use `data.result` directly; no polling.

---

## 7. Error handling

### HTTP status codes

| Code | Meaning |
|------|--------|
| 400 | Bad request: validation (invalid UUID, missing/invalid body, file type/size). |
| 403 | Forbidden: e.g. S3 access denied (misconfigured IAM). |
| 404 | Not found: video or job not found. |
| 503 | Service unavailable: S3 down or inference service unreachable/timeout. |

### Response body

Nest often returns a body like:

```json
{
  "statusCode": 400,
  "message": "file is required",
  "error": "Bad Request"
}
```

Validation errors may use an array of messages. Always handle non-2xx status and parse `message` (or equivalent) for user-facing error text.

### Frontend checklist

- Use `GET /health` to detect backend availability.
- For uploads: handle `400` (file required, type, size) and `403`/`503` (storage).
- For `POST /segment`: handle `404` (video not found) and `503` (inference).
- For `GET /videos/:id` and `GET /jobs/:id`: handle `404`.
- Use UUIDs for `id` and `videoId`/`job_id`; invalid UUID → `400`.
- In async flow: poll `GET /jobs/:id` with backoff (e.g. 5–10 s) and stop when `status` is `completed` or `failed`; consider a timeout (e.g. 5 minutes) to avoid infinite polling.

---

*Document generated for Framesense NestJS backend; use as the base for frontend development.*
