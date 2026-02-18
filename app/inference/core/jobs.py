"""Video job processing."""
import asyncio
import json
import os
import tempfile
from typing import Dict
import cv2
import numpy as np
import requests
from PIL import Image

from api.schemas import JobMessage, JobStatusResponse
from app.container import Container
from infra.exceptions import JobError, S3Error
from infra.logging import get_logger
from prometheus_client import Counter

logger = get_logger(__name__)

frames_processed_total = Counter(
    'frames_processed_total',
    'Total number of processed frames'
)


async def download_video_from_s3(
    container: Container,
    s3_key: str,
    local_path: str
) -> None:
    """Download video file from S3.
    
    Args:
        container: Application container
        s3_key: S3 object key
        local_path: Local file path to save video
        
    Raises:
        S3Error: If download fails
    """
    try:
        logger.info(f"Downloading video from S3: {s3_key}")
        container.s3_client.download_file(
            container.config.s3_bucket,
            s3_key,
            local_path
        )
        logger.info(f"Video downloaded successfully: {local_path}")
    except Exception as e:
        raise S3Error(f"Failed to download video from S3: {str(e)}") from e


async def extract_frames(
    video_path: str,
    sample_fps: float
) -> list[np.ndarray]:
    """Extract frames from video at specified FPS.
    
    Args:
        video_path: Path to video file
        sample_fps: Frames per second to extract
        
    Returns:
        List of frame arrays (BGR format)
        
    Raises:
        JobError: If frame extraction fails
    """
    try:
        logger.info(f"Extracting frames from video: {video_path} at {sample_fps} FPS")
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise JobError(f"Failed to open video file: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps / sample_fps) if sample_fps > 0 else 1
        
        frames = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                frames.append(frame)
            
            frame_count += 1
        
        cap.release()
        logger.info(f"Extracted {len(frames)} frames from video")
        return frames
        
    except Exception as e:
        raise JobError(f"Failed to extract frames: {str(e)}") from e


async def process_frame_mask(
    container: Container,
    frame: np.ndarray,
    frame_index: int
) -> Dict:
    """Process a single frame and generate masks.
    
    Args:
        container: Application container
        frame: Frame array (BGR format)
        frame_index: Frame index for naming
        
    Returns:
        Dictionary with mask data
    """
    try:
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_pil = Image.fromarray(frame_rgb)
        
        # Convert to base64 for predictor
        import base64
        import io
        buffer = io.BytesIO()
        frame_pil.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Run inference
        mask_results = await container.predictor.segment_image(image_base64)
        
        # Convert to dict format
        masks = [
            {
                "rle": m.rle,
                "bbox": m.bbox,
                "score": m.score
            }
            for m in mask_results
        ]
        
        frames_processed_total.inc()
        
        return {
            "frame_index": frame_index,
            "masks": masks
        }
        
    except Exception as e:
        logger.error(f"Failed to process frame {frame_index}: {str(e)}")
        raise JobError(f"Frame processing failed: {str(e)}") from e


async def upload_results_to_s3(
    container: Container,
    job_id: str,
    results: list[Dict]
) -> str:
    """Upload mask results to S3.
    
    Args:
        container: Application container
        job_id: Job identifier
        results: List of frame results
        
    Returns:
        S3 prefix where results are stored
    """
    try:
        result_prefix = f"results/{job_id}/"
        
        # Upload results as JSON
        results_json = json.dumps(results, indent=2)
        results_key = f"{result_prefix}masks.json"
        
        logger.info(f"Uploading results to S3: {results_key}")
        container.s3_client.put_object(
            Bucket=container.config.s3_bucket,
            Key=results_key,
            Body=results_json.encode('utf-8'),
            ContentType='application/json'
        )
        
        logger.info(f"Results uploaded successfully: {result_prefix}")
        return result_prefix
        
    except Exception as e:
        raise S3Error(f"Failed to upload results to S3: {str(e)}") from e


async def post_callback(
    callback_url: str,
    job_status: JobStatusResponse
) -> None:
    """POST job status to callback URL.
    
    Args:
        callback_url: Callback URL
        job_status: Job status response
        
    Raises:
        JobError: If callback fails
    """
    try:
        logger.info(f"Posting callback to: {callback_url}")
        response = requests.post(
            callback_url,
            json=job_status.dict(),
            timeout=10
        )
        response.raise_for_status()
        logger.info("Callback posted successfully")
    except Exception as e:
        logger.error(f"Failed to post callback: {str(e)}")
        # Don't raise - callback failure shouldn't fail the job
        raise JobError(f"Callback failed: {str(e)}") from e


async def process_video_job(
    job: JobMessage,
    container: Container
) -> None:
    """Process a video job: download, extract frames, segment, upload results.
    
    Args:
        job: Job message
        container: Application container
        
    Raises:
        JobError: If job processing fails
    """
    temp_video_path = None
    
    try:
        logger.info(f"Processing job: {job.job_id}")
        
        # Create temporary file for video
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            temp_video_path = tmp_file.name
        
        # Download video from S3
        await download_video_from_s3(container, job.s3_key, temp_video_path)
        
        # Extract frames
        frames = await extract_frames(temp_video_path, container.config.sample_fps)
        
        # Process each frame
        results = []
        for i, frame in enumerate(frames):
            frame_result = await process_frame_mask(container, frame, i)
            results.append(frame_result)
        
        # Upload results to S3
        result_prefix = await upload_results_to_s3(container, job.job_id, results)
        
        # Post callback
        job_status = JobStatusResponse(
            job_id=job.job_id,
            status="success",
            result_s3_prefix=result_prefix
        )
        await post_callback(job.callback_url, job_status)
        
        logger.info(f"Job {job.job_id} processed successfully")
        
    except Exception as e:
        logger.error(f"Job {job.job_id} failed: {str(e)}", exc_info=True)
        
        # Post error callback
        try:
            job_status = JobStatusResponse(
                job_id=job.job_id,
                status="failed",
                error=str(e)
            )
            await post_callback(job.callback_url, job_status)
        except Exception as callback_error:
            logger.error(f"Failed to post error callback: {str(callback_error)}")
        
        raise JobError(f"Job processing failed: {str(e)}") from e
        
    finally:
        # Cleanup temporary file
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except Exception as e:
                logger.warning(f"Failed to remove temp file: {str(e)}")
