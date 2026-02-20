"""Configuration settings for the SAM 3 inference service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="")

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


settings = Settings()
