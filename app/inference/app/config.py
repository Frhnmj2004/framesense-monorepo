"""Configuration management using Pydantic BaseSettings."""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Model configuration
    model_path: str = Field(
        default="facebook/sam3",
        env="MODEL_PATH",
        description="Local path or HuggingFace model ID for SAM3"
    )
    require_gpu: bool = Field(
        default=True,
        env="REQUIRE_GPU",
        description="Fail-fast if CUDA is not available"
    )

    # Server configuration
    inference_port: int = Field(
        default=8000,
        env="INFERENCE_PORT",
        description="HTTP server port"
    )
    environment: str = Field(
        default="development",
        env="ENVIRONMENT",
        description="Environment name (development, production, etc.)"
    )

    # Inference configuration
    max_concurrency: int = Field(
        default=2,
        env="MAX_CONCURRENCY",
        description="Maximum parallel inference calls"
    )
    inference_timeout: int = Field(
        default=30,
        env="INFERENCE_TIMEOUT",
        description="Per-request timeout in seconds"
    )
    sample_fps: float = Field(
        default=1.0,
        env="SAMPLE_FPS",
        description="Frames per second to extract from video"
    )

    # S3 configuration
    s3_region: str = Field(
        default="us-east-1",
        env="S3_REGION",
        description="AWS S3 region"
    )
    s3_bucket: str = Field(
        default="",
        env="S3_BUCKET",
        description="S3 bucket name"
    )
    s3_access_key_id: Optional[str] = Field(
        default=None,
        env="S3_ACCESS_KEY_ID",
        description="AWS access key ID"
    )
    s3_secret_access_key: Optional[str] = Field(
        default=None,
        env="S3_SECRET_ACCESS_KEY",
        description="AWS secret access key"
    )
    s3_endpoint: Optional[str] = Field(
        default=None,
        env="S3_ENDPOINT",
        description="S3-compatible endpoint (optional)"
    )

    # Redis configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis connection URL"
    )
    redis_job_queue: str = Field(
        default="inference:jobs",
        env="REDIS_JOB_QUEUE",
        description="Redis queue name for job processing"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def load_config() -> Config:
    """Load configuration from environment variables."""
    return Config()
