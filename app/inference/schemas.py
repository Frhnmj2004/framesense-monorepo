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


class FrameDetection(BaseModel):
    """Detection results for a single frame."""

    frame_index: int = Field(..., description="Frame index in the video")
    boxes: list[list[float]] = Field(
        ...,
        description="List of bounding boxes in [x1, y1, x2, y2] format (absolute coordinates)",
    )
    scores: list[float] = Field(
        ...,
        description="Confidence scores for each detection (0.0 to 1.0)",
    )
    mask_shape: list[int] = Field(
        ...,
        description="Shape of the mask [height, width] for reference",
    )


class VideoProcessResponse(BaseModel):
    """Response schema for video processing endpoint."""

    session_id: str = Field(..., description="SAM 3 session ID used for processing")
    frames_processed: int = Field(
        ...,
        description="Total number of frames processed",
    )
    detections: list[FrameDetection] = Field(
        ...,
        description="Detection results for each frame",
    )


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="ok", description="Service status")
