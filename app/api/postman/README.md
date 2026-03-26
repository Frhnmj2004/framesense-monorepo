# Postman Collection

## Import

1. Open Postman
2. **Import** → **Upload Files** → select `Framesense-API.postman_collection.json`
3. Or drag the file into Postman

## Variables

- **baseUrl** (default: `http://localhost:3000`) — Change for staging/production
- **videoId** — Auto-filled after Upload Video
- **jobId** — Auto-filled after Segment (sync or async)

## Flow

1. **Health Check** — Verify API is up
2. **Upload Video** — Pick an MP4 file; `videoId` is saved automatically
3. **Segment (Sync)** — Uses `videoId`; waits for inference; saves `jobId`
4. **Get Job by ID** — Uses `jobId` to fetch result

For async: run **Segment (Async)** then poll **Get Job by ID** until `status` is `completed`.
