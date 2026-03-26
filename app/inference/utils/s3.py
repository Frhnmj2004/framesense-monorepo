"""S3 helpers for uploading inference artifacts."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from config import settings

logger = logging.getLogger(__name__)


def _get_s3_client():
  session = boto3.session.Session(region_name=settings.aws_region)
  return session.client("s3", config=Config(signature_version="s3v4"))


def upload_file_to_s3(
  local_path: Path,
  s3_key: str,
  content_type: str,
) -> Optional[str]:
  """Upload a file to S3 and return the S3 key (no presigned URL).

  The backend stores this key and generates presigned URLs on demand for the
  frontend, so links do not expire at response time and access can be controlled.

  Returns the s3_key on success, None if S3 bucket is not configured.
  Raises on fatal AWS errors.
  """
  bucket = settings.s3_bucket
  if not bucket:
    logger.warning("S3 bucket not configured; skipping upload for %s", local_path)
    return None

  client = _get_s3_client()

  try:
    client.upload_file(
      Filename=str(local_path),
      Bucket=bucket,
      Key=s3_key,
      ExtraArgs={"ContentType": content_type},
    )
    return s3_key
  except (BotoCoreError, ClientError) as e:
    logger.error("Failed to upload %s to s3://%s/%s: %s", local_path, bucket, s3_key, e)
    raise

