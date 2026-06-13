"""FastAPI application entry point for SAM 3 inference service."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from config import settings
from job_store import JobStore
from sam3d_runner import Sam3DNotAvailable, run_3d
from sam_service import SamService
from schemas import (
    HealthResponse,
    Inference3DErrorResponse,
    Inference3DJobResponse,
    Inference3DRequest,
    Inference3DResultResponse,
    ModelStatusResponse,
    VideoProcessRequest,
    VideoProcessResponse,
)
from utils.rle import decode_coco_rle
from utils.s3 import upload_file_to_s3
from utils.video import cleanup_video, download_video, trim_video_to_frames

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SAM 3 Video Inference Service",
    description="GPU-based inference microservice for SAM 3 video segmentation",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize services and load SAM 3 model on startup."""
    logger.info("Starting SAM 3 inference service...")

    # Initialize SAM 3 video service
    service = SamService()
    try:
        service.load_model()
        logger.info("SAM 3 model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load SAM 3 model: {e}", exc_info=True)
        raise RuntimeError(f"Failed to initialize service: {e}") from e
    app.state.sam_service = service

    # Initialize in-memory job store for 3D jobs
    app.state.job_store = JobStore()

    logger.info("SAM 3 inference service started successfully")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup resources on shutdown."""
    logger.info("Shutting down SAM 3 inference service...")

    if hasattr(app.state, "sam_service"):
        service: SamService = app.state.sam_service
        service.shutdown()

    logger.info("SAM 3 inference service shut down")


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with status "ok"
    """
    return HealthResponse(status="ok")


@app.get("/models/status", response_model=ModelStatusResponse)
async def models_status(request: Request) -> ModelStatusResponse:
    """Report model and GPU status for operators."""
    # Optional admin token gate
    if settings.inference_admin_token:
        token = request.headers.get("x-inference-admin-token") or request.query_params.get(
            "admin_token"
        )
        if token != settings.inference_admin_token:
            raise HTTPException(status_code=403, detail="Forbidden")

    sam3_loaded = bool(getattr(app.state, "sam_service", None) and app.state.sam_service.predictor)

    sam3d_available = False
    messages: list[str] = []

    if not settings.enable_sam3d:
        messages.append("SAM-3D disabled via ENABLE_SAM3D/enable_sam3d.")
    elif not settings.sam3d_repo_path or not settings.sam3d_checkpoint_path:
        messages.append("SAM-3D not configured: set SAM3D_REPO_PATH and SAM3D_CHECKPOINT_PATH.")
    else:
        sam3d_available = True

    gpu_info: Optional[dict] = None
    try:
        import torch

        if torch.cuda.is_available():
            gpu_info = {
                "device_count": torch.cuda.device_count(),
                "current_device": torch.cuda.current_device(),
                "name": torch.cuda.get_device_name(0),
                "memory_allocated": int(torch.cuda.memory_allocated(0)),
                "memory_reserved": int(torch.cuda.memory_reserved(0)),
            }
    except Exception as e:  # pragma: no cover - best-effort
        messages.append(f"Failed to query GPU info: {e}")

    return ModelStatusResponse(
        sam3_loaded=sam3_loaded,
        sam3d_available=sam3d_available,
        gpu_memory_info=gpu_info,
        messages=messages,
    )


@app.post("/process-video", response_model=VideoProcessResponse)
async def process_video(request: VideoProcessRequest) -> VideoProcessResponse:
    """
    Process a video with SAM 3 using a text prompt.

    Args:
        request: VideoProcessRequest with video_url and text_prompt

    Returns:
        VideoProcessResponse with detection results for all frames

    Raises:
        HTTPException: For various error conditions (400, 422, 502, 500, 504)
    """
    request_start = time.perf_counter()
    logger.info(
        "[process-video] request received | video_url=%s | text_prompt=%s | max_frames=%s",
        str(request.video_url)[:80] + "..." if len(str(request.video_url)) > 80 else str(request.video_url),
        request.text_prompt[:50] + "..." if len(request.text_prompt) > 50 else request.text_prompt,
        request.max_frames,
    )

    service: SamService = app.state.sam_service

    if service is None or service.predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized. Model may still be loading.",
        )

    video_path: Path | None = None
    trimmed_path: Path | None = None

    try:
        # Validate request
        if not request.text_prompt or not request.text_prompt.strip():
            raise HTTPException(
                status_code=400,
                detail="text_prompt cannot be empty",
            )

        # Download video to temporary location
        t0 = time.perf_counter()
        logger.info("[process-video] download start | timeout=%ss", settings.video_download_timeout)
        try:
            video_path = download_video(
                url=str(request.video_url),
                timeout=settings.video_download_timeout,
                max_size_mb=settings.max_video_size_mb,
            )
            elapsed = time.perf_counter() - t0
            size_mb = video_path.stat().st_size / (1024 * 1024)
            logger.info(
                "[process-video] download done | path=%s | size_mb=%.2f | elapsed=%.1fs",
                video_path,
                size_mb,
                elapsed,
            )
        except ValueError as e:
            logger.error("[process-video] download failed | error=%s", e)
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download video: {str(e)}",
            ) from e

        # Trim to first N frames so the model loads less (avoids OOM and very long GPU-heavy runs)
        effective_max_frames: int | None = (
            request.max_frames if request.max_frames is not None else (settings.default_max_frames or None)
        )
        if effective_max_frames is not None and effective_max_frames <= 0:
            effective_max_frames = None
        path_to_process: Path = video_path
        if effective_max_frames is not None:
            t1 = time.perf_counter()
            logger.info("[process-video] trim start | max_frames=%s", effective_max_frames)
            try:
                trimmed_path = trim_video_to_frames(video_path, effective_max_frames)
                path_to_process = trimmed_path
                elapsed_trim = time.perf_counter() - t1
                logger.info(
                    "[process-video] trim done | path=%s | elapsed=%.1fs",
                    trimmed_path,
                    elapsed_trim,
                )
            except ValueError as e:
                logger.error("[process-video] trim failed | error=%s", e)
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to trim video: {str(e)}",
                ) from e

        # Process video with SAM 3 (run in thread pool so event loop stays responsive)
        t2 = time.perf_counter()
        logger.info(
            "[process-video] inference start | path=%s | prompt=%s",
            path_to_process,
            request.text_prompt.strip()[:40],
        )
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: service.process_video(
                    video_path=str(path_to_process),
                    text_prompt=request.text_prompt.strip(),
                    max_frames=None,  # We already trimmed; process all frames in trimmed clip
                ),
            )
            elapsed_infer = time.perf_counter() - t2
            logger.info(
                "[process-video] inference done | frames_processed=%s | elapsed=%.1fs",
                response.frames_processed,
                elapsed_infer,
            )
            total_elapsed = time.perf_counter() - request_start
            logger.info("[process-video] request complete | total_elapsed=%.1fs", total_elapsed)
            return response
        except RuntimeError as e:
            logger.error("[process-video] inference error | error=%s", e, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Inference failed: {str(e)}",
            ) from e
        except Exception as e:
            logger.error("[process-video] unexpected error | error=%s", e, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}",
            ) from e

    finally:
        # Always cleanup temporary video file(s)
        if trimmed_path is not None:
            try:
                cleanup_video(trimmed_path)
                logger.debug(f"Cleaned up trimmed video: {trimmed_path}")
            except Exception as e:
                logger.warning(f"Error cleaning up trimmed video: {e}")
        if video_path is not None:
            try:
                cleanup_video(video_path)
                logger.debug(f"Cleaned up temporary video: {video_path}")
            except Exception as e:
                logger.warning(f"Error cleaning up video file: {e}")


@app.post("/3d", response_model=Inference3DJobResponse | Inference3DResultResponse)
async def create_3d_job(request_body: Inference3DRequest) -> Inference3DJobResponse | Inference3DResultResponse:
    """Create and optionally run a 3D reconstruction job.

    For now, jobs are executed inline and stored in memory. The API surface
    still exposes a job_id and allows polling via GET /3d/{job_id}.
    """
    if not settings.enable_sam3d:
        raise HTTPException(status_code=503, detail="SAM-3D disabled by configuration")

    # Basic validation of SAM-3D configuration before doing any work
    try:
        # This will raise Sam3DNotAvailable if misconfigured
        _ = (settings.sam3d_repo_path, settings.sam3d_checkpoint_path)
        if not _[0] or not _[1]:
            raise Sam3DNotAvailable("SAM-3D repo/checkpoints not configured")
    except Sam3DNotAvailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    import uuid

    job_id = request_body.job_id or str(uuid.uuid4())

    # Decode RLE mask to (H, W) boolean array
    size = request_body.mask_rle.size
    if len(size) < 2:
        raise HTTPException(status_code=400, detail="mask_rle.size must be [height, width]")
    mask = decode_coco_rle(request_body.mask_rle.counts, (size[0], size[1]))

    # Download image to a local path under the inference workdir
    workdir = Path(settings.inference_workdir) / "jobs" / job_id
    workdir.mkdir(parents=True, exist_ok=True)
    image_path = workdir / "image.png"

    try:
        import requests

        resp = requests.get(str(request_body.image_url), timeout=settings.video_download_timeout)
        resp.raise_for_status()
        with open(image_path, "wb") as f:
            f.write(resp.content)
    except Exception as e:
        logger.error("[3d] failed to download image: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to download image: {e}") from e

    job_store: JobStore = app.state.job_store
    job_store.enqueue(job_id)

    # Execute the job inline for now (no separate worker loop)
    start = time.perf_counter()
    try:
        runner_out = run_3d(
            image_path=image_path,
            mask=mask,
            seed=request_body.seed,
            preset=request_body.preset,
            workdir=workdir,
        )
        elapsed = time.perf_counter() - start

        mesh_files = []

        ply_path: Optional[Path] = runner_out.get("ply_path")
        glb_path: Optional[Path] = runner_out.get("glb_path")
        preview_path: Optional[Path] = runner_out.get("preview_path")

        # Upload artifacts to S3; return S3 keys only (backend stores them and issues presigned URLs to frontend)
        s3_prefix = f"3d/{job_id}"
        preview_s3_key: Optional[str] = None
        if preview_path and preview_path.exists():
            preview_s3_key = upload_file_to_s3(
                preview_path, f"{s3_prefix}/preview.png", "image/png"
            )

        if ply_path and ply_path.exists():
            key = upload_file_to_s3(
                ply_path, f"{s3_prefix}/splat.ply", "application/octet-stream"
            )
            if key:
                mesh_files.append({"type": "ply", "s3_key": key})

        if glb_path and glb_path.exists():
            key = upload_file_to_s3(
                glb_path, f"{s3_prefix}/model.glb", "model/gltf-binary"
            )
            if key:
                mesh_files.append({"type": "glb", "s3_key": key})

        result = Inference3DResultResponse(
            job_id=job_id,
            status="completed",
            preview_s3_key=preview_s3_key,
            preview_url=None,
            preview_base64=None,
            mesh_files=mesh_files,
            runtime_seconds=elapsed,
        )
        job_store.set_completed(job_id, result)

        # For now always return completed result synchronously
        return result
    except Sam3DNotAvailable as e:
        job_store.set_failed(job_id, str(e))
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error("[3d] job failed | job_id=%s | error=%s", job_id, e, exc_info=True)
        job_store.set_failed(job_id, str(e))
        raise HTTPException(status_code=500, detail=f"3D inference failed: {e}") from e


@app.get("/3d/{job_id}", response_model=Inference3DResultResponse | Inference3DErrorResponse | Inference3DJobResponse)
async def get_3d_job(job_id: str) -> Inference3DResultResponse | Inference3DErrorResponse | Inference3DJobResponse:
    """Get status or result for a 3D reconstruction job."""
    job_store: JobStore = app.state.job_store
    entry = job_store.get(job_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if entry.status == "completed" and entry.result is not None:
        return entry.result
    if entry.status == "failed" and entry.error is not None:
        return Inference3DErrorResponse(job_id=job_id, status="failed", error=entry.error)

    # queued or running
    return Inference3DJobResponse(job_id=job_id, status="queued")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
