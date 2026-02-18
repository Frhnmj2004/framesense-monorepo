"""Custom exceptions for the inference service."""


class InferenceServiceError(Exception):
    """Base exception for inference service errors."""
    pass


class ModelLoadError(InferenceServiceError):
    """Raised when model loading fails."""
    pass


class InferenceError(InferenceServiceError):
    """Raised when inference fails."""
    pass


class InferenceTimeoutError(InferenceError):
    """Raised when inference exceeds timeout."""
    pass


class S3Error(InferenceServiceError):
    """Raised when S3 operations fail."""
    pass


class JobError(InferenceServiceError):
    """Raised when job processing fails."""
    pass


class ValidationError(InferenceServiceError):
    """Raised when request validation fails."""
    pass
