"""Pydantic request/response schemas for API endpoints."""
from pydantic import BaseModel, Field
from typing import List, Optional


class MaskResult(BaseModel):
    """Segmentation mask result."""
    rle: str = Field(..., description="Run-Length Encoded mask string")
    bbox: List[int] = Field(..., description="Bounding box [x, y, width, height]")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class SegmentRequest(BaseModel):
    """Request for image segmentation."""
    image_base64: str = Field(..., description="Base64 encoded image")
    prompt: Optional[str] = Field(
        default=None,
        description="Optional text prompt for segmentation"
    )


class SegmentResponse(BaseModel):
    """Response for image segmentation."""
    success: bool = Field(default=True)
    masks: List[MaskResult] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="ok")


class JobMessage(BaseModel):
    """Redis job message schema."""
    job_id: str = Field(..., description="Unique job identifier")
    s3_key: str = Field(..., description="S3 key for input video")
    callback_url: str = Field(..., description="URL to POST results to")


class JobStatusResponse(BaseModel):
    """Job status callback response."""
    job_id: str
    status: str = Field(..., description="Status: success, failed, processing")
    result_s3_prefix: Optional[str] = Field(
        default=None,
        description="S3 prefix where mask results are stored"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
