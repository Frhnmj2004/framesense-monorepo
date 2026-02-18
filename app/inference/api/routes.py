"""FastAPI routes for inference service."""
import asyncio
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

from api.schemas import SegmentRequest, SegmentResponse, HealthResponse
from app.container import Container
from infra.exceptions import InferenceError, InferenceTimeoutError
from infra.logging import get_logger

logger = get_logger(__name__)

# Prometheus metrics
inference_requests_total = Counter(
    'inference_requests_total',
    'Total number of inference requests',
    ['status']
)
inference_requests_failed = Counter(
    'inference_requests_failed',
    'Total number of failed inference requests'
)
jobs_processed_total = Counter(
    'jobs_processed_total',
    'Total number of processed jobs',
    ['status']
)
frames_processed_total = Counter(
    'frames_processed_total',
    'Total number of processed frames'
)

router = APIRouter()


class AuthMiddleware(BaseHTTPMiddleware):
    """Auth stub middleware for future token validation.
    
    TODO: AUTH - Implement token validation in Phase 2
    """
    
    async def dispatch(self, request: Request, call_next):
        # Check for internal token header
        token = request.headers.get("X-Internal-Token")
        if token:
            logger.debug("Internal token header present")
        # Pass through for Phase 1
        response = await call_next(request)
        return response


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@router.post("/v1/segment", response_model=SegmentResponse)
async def segment_image(
    request: SegmentRequest,
    request_obj: Request
):
    """Segment image using SAM 3.
    
    TODO: GRPC - This endpoint can be migrated to gRPC in Phase 2
    """
    container: Container = request_obj.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Container not initialized")
    
    inference_requests_total.labels(status="received").inc()
    
    try:
        # Convert MaskResult NamedTuple to dict for response
        mask_results = await container.predictor.segment_image(
            request.image_base64,
            request.prompt
        )
        
        # Convert to response format
        masks = [
            {
                "rle": m.rle,
                "bbox": m.bbox,
                "score": m.score
            }
            for m in mask_results
        ]
        
        inference_requests_total.labels(status="success").inc()
        
        return SegmentResponse(success=True, masks=masks)
        
    except InferenceTimeoutError as e:
        inference_requests_total.labels(status="timeout").inc()
        inference_requests_failed.inc()
        logger.error(f"Inference timeout: {str(e)}")
        raise HTTPException(status_code=504, detail=str(e))
        
    except InferenceError as e:
        inference_requests_total.labels(status="error").inc()
        inference_requests_failed.inc()
        logger.error(f"Inference error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        inference_requests_total.labels(status="error").inc()
        inference_requests_failed.inc()
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def register_routes(app, container: Container):
    """Register routes with FastAPI app."""
    # Store container in app state for route access
    app.state.container = container
    
    # Add auth middleware
    app.add_middleware(AuthMiddleware)
    
    # Include router
    app.include_router(router)
