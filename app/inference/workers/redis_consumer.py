"""Redis job consumer with idempotency."""
import asyncio
import json
from typing import Optional

from api.schemas import JobMessage
from app.container import Container
from core.jobs import process_video_job
from infra.exceptions import JobError
from infra.logging import get_logger
from prometheus_client import Counter

logger = get_logger(__name__)

jobs_processed_total = Counter(
    'jobs_processed_total',
    'Total number of processed jobs',
    ['status']
)


class RedisConsumer:
    """Redis job consumer."""

    def __init__(self, container: Container):
        """Initialize consumer.
        
        Args:
            container: Application container
        """
        self.container = container
        self.running = False
        self.logger = get_logger(__name__)

    def _check_idempotency(self, job_id: str) -> bool:
        """Check if job has already been processed (idempotency check).
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job should be processed, False if already processed
        """
        try:
            key = f"job:{job_id}:status"
            # Try to set key with NX (only if not exists) and expiration
            result = self.container.redis_client.set(
                key,
                "processing",
                nx=True,
                ex=3600  # 1 hour expiration
            )
            return result is not None  # True if key was set (new job)
        except Exception as e:
            logger.error(f"Idempotency check failed: {str(e)}")
            # On error, allow processing (fail open)
            return True

    def _parse_job_message(self, message: str) -> Optional[JobMessage]:
        """Parse job message from Redis.
        
        Args:
            message: JSON string message
            
        Returns:
            JobMessage or None if parsing fails
        """
        try:
            data = json.loads(message)
            return JobMessage(**data)
        except Exception as e:
            logger.error(f"Failed to parse job message: {str(e)}")
            return None

    async def _process_job(self, job: JobMessage) -> None:
        """Process a single job.
        
        Args:
            job: Job message
        """
        try:
            logger.info(f"Processing job: {job.job_id}")
            await process_video_job(job, self.container)
            jobs_processed_total.labels(status="success").inc()
            logger.info(f"Job {job.job_id} completed successfully")
        except JobError as e:
            jobs_processed_total.labels(status="failed").inc()
            logger.error(f"Job {job.job_id} failed: {str(e)}")
        except Exception as e:
            jobs_processed_total.labels(status="error").inc()
            logger.error(f"Unexpected error processing job {job.job_id}: {str(e)}", exc_info=True)

    async def _consume_loop(self) -> None:
        """Main consumption loop."""
        queue_name = self.container.config.redis_job_queue
        
        logger.info(f"Starting Redis consumer for queue: {queue_name}")
        
        while self.running:
            try:
                # BLPOP blocks until a message is available
                result = self.container.redis_client.blpop(queue_name, timeout=1)
                
                if result is None:
                    # Timeout - continue loop
                    continue
                
                queue, message = result
                
                # Parse job message
                job = self._parse_job_message(message)
                if job is None:
                    continue
                
                # Check idempotency
                if not self._check_idempotency(job.job_id):
                    logger.info(f"Job {job.job_id} already processed, skipping")
                    jobs_processed_total.labels(status="skipped").inc()
                    continue
                
                # Process job
                await self._process_job(job)
                
            except Exception as e:
                logger.error(f"Error in consume loop: {str(e)}", exc_info=True)
                # Wait before retrying
                await asyncio.sleep(1)

    async def start(self) -> None:
        """Start the consumer."""
        self.running = True
        logger.info("Redis consumer started")
        await self._consume_loop()

    def stop(self) -> None:
        """Stop the consumer."""
        self.running = False
        logger.info("Redis consumer stopped")


async def run_consumer(container: Container) -> None:
    """Run Redis consumer (entry point for worker process).
    
    Args:
        container: Application container
    """
    consumer = RedisConsumer(container)
    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt, stopping consumer...")
        consumer.stop()
    except Exception as e:
        logger.error(f"Consumer error: {str(e)}", exc_info=True)
        raise
