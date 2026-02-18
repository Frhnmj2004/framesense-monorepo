"""Main entry point for inference service."""
import asyncio
import signal
import sys
import torch
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import Config as UvicornConfig, Server

from app.config import load_config
from app.container import Container
from api.routes import register_routes
from infra.exceptions import ModelLoadError
from infra.logging import setup_logger, get_logger

# Setup logger
logger = setup_logger(__name__)

# Global container instance
container: Container = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI."""
    global container
    
    # Startup
    logger.info("Starting inference service...")
    
    # Load configuration
    config = load_config()
    
    # Check CUDA availability if required
    if config.require_gpu:
        if not torch.cuda.is_available():
            error_msg = (
                "CUDA is not available but REQUIRE_GPU=true. "
                "Set REQUIRE_GPU=false for CPU-only mode or ensure CUDA is available."
            )
            logger.error(error_msg)
            sys.exit(1)
        logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
    
    # Initialize container
    try:
        container = Container(config)
        # Register routes after container is ready
        register_routes(app, container)
        logger.info("Inference service started successfully")
    except ModelLoadError as e:
        logger.error(f"Failed to load model: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to initialize container: {str(e)}", exc_info=True)
        sys.exit(1)
    
    yield
    
    # Shutdown
    logger.info("Shutting down inference service...")
    if container:
        container.shutdown()
    logger.info("Inference service stopped")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Video Annotation Platform - Inference Service",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Routes will be registered after container is initialized in lifespan
    
    return app


def get_container() -> Container:
    """Get container instance (for dependency injection)."""
    return container


async def shutdown_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    # Uvicorn handles graceful shutdown automatically
    sys.exit(0)


def main():
    """Main entry point."""
    # Register signal handlers
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    
    # Load config
    config = load_config()
    
    # Create app
    app = create_app()
    
    # Create uvicorn config
    uvicorn_config = UvicornConfig(
        app=app,
        host="0.0.0.0",
        port=config.inference_port,
        log_config=None,  # Use our custom logging
    )
    
    # Create server
    server = Server(uvicorn_config)
    
    # Run server
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
