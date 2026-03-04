"""FastAPI application entry point for SAM 3 inference service."""

# Patch autocast before any code (including sam3) is loaded, so SAM 3 always sees disabled autocast
import os
if os.environ.get("DISABLE_SAM3_AUTOCAST", "").strip().lower() in ("1", "true", "yes"):
    import torch
    _orig_autocast = torch.amp.autocast
    def _autocast_disabled(*args: object, enabled: bool = True, **kwargs: object):  # noqa: E501
        return _orig_autocast(*args, enabled=False, **kwargs)
    torch.amp.autocast = _autocast_disabled  # type: ignore[assignment]
    if getattr(torch, "autocast", None) is not None:
        torch.autocast = _autocast_disabled  # type: ignore[assignment]

import asyncio
import logging
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from config import settings
from sam_service import SamService
from schemas import HealthResponse, VideoProcessRequest, VideoProcessResponse
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
    """Initialize SAM service and load model on startup."""
    logger.info("Starting SAM 3 inference service...")

    # Initialize SAM service
    service = SamService()

    # Load model (this may take a while on first run)
    try:
        service.load_model()
        logger.info("SAM 3 model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load SAM 3 model: {e}", exc_info=True)
        raise RuntimeError(f"Failed to initialize service: {e}") from e

    # Store service in app state
    app.state.sam_service = service

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
