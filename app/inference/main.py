"""FastAPI application entry point for SAM 3 inference service."""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from config import settings
from sam_service import SamService
from schemas import HealthResponse, VideoProcessRequest, VideoProcessResponse
from utils.video import cleanup_video, download_video

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
    service: SamService = app.state.sam_service

    if service is None or service.predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized. Model may still be loading.",
        )

    video_path: Path | None = None

    try:
        # Validate request
        if not request.text_prompt or not request.text_prompt.strip():
            raise HTTPException(
                status_code=400,
                detail="text_prompt cannot be empty",
            )

        # Download video to temporary location
        logger.info(f"Downloading video from: {request.video_url}")
        try:
            video_path = download_video(
                url=str(request.video_url),
                timeout=settings.video_download_timeout,
                max_size_mb=settings.max_video_size_mb,
            )
            logger.info(f"Video downloaded to: {video_path}")
        except ValueError as e:
            logger.error(f"Video download failed: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download video: {str(e)}",
            ) from e

        # Process video with SAM 3
        logger.info(f"Processing video with prompt: '{request.text_prompt}'")
        try:
            response = service.process_video(
                video_path=str(video_path),
                text_prompt=request.text_prompt.strip(),
            )
            logger.info(
                f"Video processing completed: {response.frames_processed} frames processed"
            )
            return response
        except RuntimeError as e:
            logger.error(f"Inference error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Inference failed: {str(e)}",
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during inference: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}",
            ) from e

    finally:
        # Always cleanup temporary video file
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
