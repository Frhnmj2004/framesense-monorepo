"""Configuration settings for the SAM 3 inference service."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # HuggingFace token for accessing gated SAM 3 model checkpoints
    # Required: SAM 3 requires authentication to download checkpoints
    # Set via: HF_TOKEN=your_token_here
    hf_token: str | None = Field(
        default=None,
        description="HuggingFace access token for SAM 3 checkpoint download",
    )

    # Device for model inference
    # Defaults to "cuda" if CUDA is available, otherwise "cpu"
    model_device: str = Field(
        default="cuda",
        description="Device to run inference on (cuda or cpu)",
    )

    # Video download constraints
    max_video_size_mb: int = Field(
        default=500,
        description="Maximum video file size in MB",
    )

    video_download_timeout: int = Field(
        default=120,
        description="Video download timeout in seconds",
    )

    # Cap frames when client does not send max_frames (0 = no cap, process full video).
    # 90 = safe for 6–12 GB VRAM; 300 = reasonable for A40/24GB+; 0 = no limit.
    default_max_frames: int = Field(
        default=300,
        ge=0,
        description="Default max frames when request omits max_frames (0 = no cap)",
    )

    # Inference timeout per request
    inference_timeout: int = Field(
        default=300,
        description="Maximum time for inference per request in seconds",
    )

    # Server configuration
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the server to",
    )

    port: int = Field(
        default=8000,
        description="Port to bind the server to",
    )

    # --- SAM-3D and 3D inference configuration ---

    enable_sam3d: bool = Field(
        default=True,
        description="Enable SAM-3D 3D reconstruction endpoints",
    )

    sam3d_checkpoint_path: str | None = Field(
        default=None,
        description="Path to SAM-3D checkpoints directory (contains pipeline.yaml)",
    )

    sam3d_repo_path: str | None = Field(
        default=None,
        description="Path to local sam-3d-objects repository (for importing inference code)",
    )

    inference_workdir: str = Field(
        default="workdir",
        description="Base directory for temporary 3D jobs (frames, meshes, previews)",
    )

    default_sync_timeout_ms: int = Field(
        default=120_000,
        description="Default timeout in milliseconds for synchronous 3D jobs",
    )

    model_max_idle_seconds: int = Field(
        default=300,
        description="Maximum idle time before eligible models may be unloaded (for future use)",
    )

    # S3 configuration for 3D artifacts
    s3_bucket: str | None = Field(
        default=None,
        description="S3 bucket name for uploading 3D artifacts (preview, meshes)",
    )

    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for S3 operations",
    )

    # Optional admin token for protected model/status endpoints
    inference_admin_token: str | None = Field(
        default=None,
        description="Optional admin token required for sensitive admin endpoints",
    )


settings = Settings()
