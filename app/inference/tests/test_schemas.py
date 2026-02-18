"""Schema validation tests."""
import pytest
from pydantic import ValidationError

from api.schemas import (
    SegmentRequest,
    SegmentResponse,
    MaskResult,
    HealthResponse,
    JobMessage,
    JobStatusResponse
)


def test_segment_request_valid():
    """Test valid segment request."""
    request = SegmentRequest(
        image_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        prompt="test prompt"
    )
    assert request.image_base64 is not None
    assert request.prompt == "test prompt"


def test_segment_request_no_prompt():
    """Test segment request without prompt."""
    request = SegmentRequest(
        image_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    assert request.prompt is None


def test_mask_result_valid():
    """Test valid mask result."""
    mask = MaskResult(
        rle="test_rle",
        bbox=[10, 20, 100, 200],
        score=0.95
    )
    assert mask.rle == "test_rle"
    assert mask.bbox == [10, 20, 100, 200]
    assert mask.score == 0.95


def test_mask_result_score_validation():
    """Test mask result score validation."""
    # Valid score
    mask = MaskResult(rle="test", bbox=[0, 0, 10, 10], score=0.5)
    assert mask.score == 0.5
    
    # Invalid score (too high)
    with pytest.raises(ValidationError):
        MaskResult(rle="test", bbox=[0, 0, 10, 10], score=1.5)
    
    # Invalid score (negative)
    with pytest.raises(ValidationError):
        MaskResult(rle="test", bbox=[0, 0, 10, 10], score=-0.1)


def test_health_response():
    """Test health response."""
    response = HealthResponse()
    assert response.status == "ok"


def test_job_message():
    """Test job message schema."""
    job = JobMessage(
        job_id="test-job-123",
        s3_key="videos/test.mp4",
        callback_url="http://example.com/callback"
    )
    assert job.job_id == "test-job-123"
    assert job.s3_key == "videos/test.mp4"
    assert job.callback_url == "http://example.com/callback"


def test_job_status_response():
    """Test job status response."""
    status = JobStatusResponse(
        job_id="test-job-123",
        status="success",
        result_s3_prefix="results/test-job-123/"
    )
    assert status.job_id == "test-job-123"
    assert status.status == "success"
    assert status.result_s3_prefix == "results/test-job-123/"
