"""Pydantic schemas for request and response models."""

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
