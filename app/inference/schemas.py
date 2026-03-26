"""Pydantic schemas for request and response models."""

from typing import Literal, Any

from pydantic import BaseModel, Field, HttpUrl


class VideoProcessRequest(BaseModel):
    """Request schema for video processing endpoint."""

    video_url: HttpUrl = Field(
        ...,
        description="URL of the video file to process (MP4 format)",
    )
    text_prompt: str = Field(
        ...,
        min_length=1,
        description="Text prompt describing objects to detect and segment",
    )
    max_frames: int | None = Field(
        default=None,
        ge=1,
        description="Optional cap on number of frames to process (reduces memory use for long videos)",
    )


class MaskRLE(BaseModel):
    """COCO-style run-length encoded binary mask."""

    counts: str = Field(
        ...,
        description="Run-length encoded mask as a string (COCO uncompressed RLE format)",
    )
    size: list[int] = Field(
        ...,
        description="Mask dimensions [height, width]",
    )


class ObjectDetection(BaseModel):
    """A single detected/tracked object within a frame."""

    object_id: int = Field(..., description="Unique object ID (consistent across frames for tracking)")
    score: float = Field(..., description="Detection confidence (0.0 to 1.0)")
    box: list[float] = Field(
        ...,
        description="Bounding box [x1, y1, x2, y2] in absolute pixel coordinates",
    )
    mask_rle: MaskRLE = Field(
        ...,
        description="Pixel-level segmentation mask in COCO RLE format",
    )


class FrameDetection(BaseModel):
    """Detection results for a single frame."""

    frame_index: int = Field(..., description="Frame index in the video")
    objects: list[ObjectDetection] = Field(
        default_factory=list,
        description="Detected/tracked objects in this frame",
    )


class VideoProcessResponse(BaseModel):
    """Response schema for video processing endpoint."""

    session_id: str = Field(..., description="SAM 3 session ID used for processing")
    frames_processed: int = Field(..., description="Total number of frames processed")
    video_width: int = Field(..., description="Video width in pixels")
    video_height: int = Field(..., description="Video height in pixels")
    detections: list[FrameDetection] = Field(
        ...,
        description="Detection results for each frame",
    )


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="ok", description="Service status")


# --- 3D inference schemas ---


class Inference3DRequest(BaseModel):
    """Request schema for single-image 3D reconstruction."""

    image_url: HttpUrl = Field(
        ...,
        description="URL of the image containing the object to reconstruct",
    )
    mask_rle: MaskRLE = Field(
        ...,
        description="Segmentation mask in COCO RLE format at source image resolution",
    )
    preset: Literal["fast", "quality"] = Field(
        default="fast",
        description='Quality preset ("fast" for lower VRAM/latency, "quality" for best results)',
    )
    seed: int | None = Field(
        default=None,
        description="Optional random seed for reproducible reconstruction",
    )
    job_id: str | None = Field(
        default=None,
        description="Optional client-supplied job identifier; if omitted, server generates one",
    )
    callback_url: HttpUrl | None = Field(
        default=None,
        description="Optional callback URL to receive async completion notifications",
    )
    object_id: int | None = Field(
        default=None,
        description="Optional object identifier when mask encodes multiple objects",
    )


class Inference3DJobResponse(BaseModel):
    """Queued 3D job response."""

    job_id: str = Field(..., description="Unique job identifier")
    status: Literal["queued"] = Field(
        default="queued",
        description="Job status",
    )


class MeshFileDescriptor(BaseModel):
    """Descriptor for a generated 3D artifact (S3 key for backend to store and sign)."""

    type: str = Field(..., description='Artifact type, e.g. "ply" or "glb"')
    s3_key: str = Field(..., description="S3 object key for backend to generate presigned URL on demand")
    url: str | None = Field(
        default=None,
        description="Deprecated: use backend artifact endpoint with s3_key instead",
    )


class Inference3DResultResponse(BaseModel):
    """Completed 3D job response. Returns S3 keys; backend stores them and issues presigned URLs to frontend."""

    job_id: str = Field(..., description="Unique job identifier")
    status: Literal["completed"] = Field(
        default="completed",
        description="Job status",
    )
    preview_s3_key: str | None = Field(
        default=None,
        description="S3 key for preview image; backend generates presigned URL when frontend requests it",
    )
    preview_url: str | None = Field(
        default=None,
        description="Deprecated: prefer preview_s3_key and backend artifact endpoint",
    )
    preview_base64: str | None = Field(
        default=None,
        description="Optional base64-encoded preview image (for small sync responses)",
    )
    mesh_files: list[MeshFileDescriptor] = Field(
        default_factory=list,
        description="List of generated mesh artifacts (type + s3_key for backend)",
    )
    runtime_seconds: float = Field(
        ...,
        description="Total runtime for the 3D reconstruction job in seconds",
    )


class Inference3DErrorResponse(BaseModel):
    """Failed 3D job response."""

    job_id: str = Field(..., description="Unique job identifier")
    status: Literal["failed"] = Field(
        default="failed",
        description="Job status",
    )
    error: str = Field(..., description="Error message")


class ModelStatusResponse(BaseModel):
    """Model and GPU status information."""

    sam3_loaded: bool = Field(..., description="Whether SAM 3 video predictor is loaded")
    sam3d_available: bool = Field(..., description="Whether SAM-3D appears available/configured")
    gpu_memory_info: dict[str, Any] | None = Field(
        default=None,
        description="Optional GPU memory information (implementation-defined)",
    )
    messages: list[str] = Field(
        default_factory=list,
        description="Human-readable status or warning messages",
    )
