"""Dependency injection container."""
import redis
import boto3
from botocore.config import Config as BotoConfig

from app.config import Config
from core.model_loader import load_model
from core.predictor import Predictor
from infra.logging import get_logger

logger = get_logger(__name__)


class Container:
    """Dependency injection container for application components."""

    def __init__(self, config: Config):
        """Initialize container with all dependencies.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Load model
        logger.info("Loading SAM 3 model...")
        self.model, self.processor, self.device = load_model(config)
        
        # Initialize predictor
        self.predictor = Predictor(
            self.model,
            self.processor,
            self.device,
            config
        )
        
        # Initialize S3 client
        self.s3_client = self._create_s3_client()
        
        # Initialize Redis client
        self.redis_client = self._create_redis_client()
        
        logger.info("Container initialized successfully")

    def _create_s3_client(self):
        """Create S3 client."""
        try:
            s3_config = {
                'region_name': self.config.s3_region,
            }
            
            if self.config.s3_endpoint:
                s3_config['endpoint_url'] = self.config.s3_endpoint
            
            # Create client with credentials if provided
            if self.config.s3_access_key_id and self.config.s3_secret_access_key:
                session = boto3.Session(
                    aws_access_key_id=self.config.s3_access_key_id,
                    aws_secret_access_key=self.config.s3_secret_access_key,
                )
                return session.client('s3', **s3_config)
            else:
                # Use default credentials (IAM role, env vars, etc.)
                return boto3.client('s3', **s3_config)
                
        except Exception as e:
            logger.error(f"Failed to create S3 client: {str(e)}")
            raise

    def _create_redis_client(self):
        """Create Redis client."""
        try:
            return redis.from_url(
                self.config.redis_url,
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Failed to create Redis client: {str(e)}")
            raise

    def shutdown(self):
        """Cleanup resources."""
        logger.info("Shutting down container...")
        if self.redis_client:
            self.redis_client.close()
        logger.info("Container shutdown complete")
