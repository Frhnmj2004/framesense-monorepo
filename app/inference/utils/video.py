"""Video download and cleanup utilities."""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def download_video(
    url: str,
    timeout: int = 120,
    max_size_mb: int = 500,
) -> Path:
    """
    Download a video file from a URL to a temporary directory.

    Args:
        url: URL of the video file to download
        timeout: Download timeout in seconds
        max_size_mb: Maximum file size in MB

    Returns:
        Path to the downloaded video file

    Raises:
        ValueError: If Content-Type is not video or file size exceeds limit
        requests.RequestException: If download fails
    """
    max_size_bytes = max_size_mb * 1024 * 1024

    # Create temporary directory for video storage
    temp_dir = Path(tempfile.mkdtemp(prefix="sam3_video_"))
    video_path = temp_dir / "video.mp4"

    try:
        logger.info("[video] download start | url=%s", url[:80] + "..." if len(url) > 80 else url)
        # Stream download with size check
        response = requests.get(url, stream=True, timeout=timeout)

        # Check Content-Type
        content_type = response.headers.get("Content-Type", "").lower()
        if not content_type.startswith("video/"):
            # Allow application/octet-stream as fallback
            if content_type != "application/octet-stream":
                raise ValueError(
                    f"Invalid Content-Type: {content_type}. Expected video/* or application/octet-stream"
                )

        # Stream to file with size limit
        total_size = 0
        with open(video_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    total_size += len(chunk)
                    if total_size > max_size_bytes:
                        raise ValueError(
                            f"Video file exceeds maximum size limit of {max_size_mb}MB"
                        )
                    f.write(chunk)

        # Verify file was downloaded
        if not video_path.exists() or video_path.stat().st_size == 0:
            raise ValueError("Downloaded video file is empty or does not exist")

        size_mb = total_size / (1024 * 1024)
        logger.info("[video] download done | path=%s | size_mb=%.2f", video_path, size_mb)
        return video_path

    except requests.RequestException as e:
        # Cleanup on error
        if video_path.exists():
            video_path.unlink()
        if temp_dir.exists():
            temp_dir.rmdir()
        raise ValueError(f"Failed to download video from {url}: {str(e)}") from e


def trim_video_to_frames(source: Path, max_frames: int) -> Path:
    """
    Trim video to the first max_frames frames using ffmpeg.
    Writes to a new file in the same directory as source.

    Args:
        source: Path to the source video file
        max_frames: Maximum number of frames to keep

    Returns:
        Path to the trimmed video file

    Raises:
        ValueError: If ffmpeg fails
    """
    if max_frames < 1:
        raise ValueError("max_frames must be >= 1")
    dest = source.parent / "video_trimmed.mp4"
    logger.info("[video] trim start | source=%s | max_frames=%s", source, max_frames)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vframes",
        str(max_frames),
        "-c",
        "copy",
        str(dest),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0 or not dest.exists():
        raise ValueError(
            f"ffmpeg trim failed: {result.stderr or result.stdout or 'unknown'}"
        )
    logger.info("[video] trim done | dest=%s", dest)
    return dest


def cleanup_video(path: Path) -> None:
    """
    Clean up a temporary video file and its parent directory.

    Args:
        path: Path to the video file (parent directory will be removed)
    """
    if path.exists():
        path.unlink()

    # Remove parent directory if it's a temp directory
    parent_dir = path.parent
    if parent_dir.exists() and parent_dir.name.startswith("sam3_video_"):
        try:
            shutil.rmtree(parent_dir)
        except OSError:
            # Ignore errors during cleanup (file may already be deleted)
            pass
