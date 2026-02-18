"""SAM 3 model loading with CUDA validation."""
import torch
from transformers import Sam3Model, Sam3Processor
from typing import Tuple

from app.config import Config
from infra.exceptions import ModelLoadError
from infra.logging import get_logger

logger = get_logger(__name__)


def check_cuda_availability(require_gpu: bool = True) -> str:
    """Check CUDA availability and return device string.
    
    Args:
        require_gpu: If True, raise error when CUDA is not available
        
    Returns:
        Device string ('cuda' or 'cpu')
        
    Raises:
        ModelLoadError: If require_gpu=True and CUDA is not available
    """
    if torch.cuda.is_available():
        device = "cuda"
        logger.info(f"CUDA available. Device: {torch.cuda.get_device_name(0)}")
        return device
    
    if require_gpu:
        error_msg = (
            "CUDA is not available but REQUIRE_GPU=true. "
            "Set REQUIRE_GPU=false for CPU-only mode."
        )
        logger.error(error_msg)
        raise ModelLoadError(error_msg)
    
    logger.warning("CUDA not available, using CPU mode")
    return "cpu"


def load_model(config: Config) -> Tuple[Sam3Model, Sam3Processor, str]:
    """Load SAM 3 model and processor.
    
    Args:
        config: Application configuration
        
    Returns:
        Tuple of (model, processor, device)
        
    Raises:
        ModelLoadError: If model loading fails
    """
    try:
        # Check CUDA availability
        device = check_cuda_availability(config.require_gpu)
        
        logger.info(f"Loading SAM 3 model from: {config.model_path}")
        
        # Load processor first
        processor = Sam3Processor.from_pretrained(config.model_path)
        logger.info("Processor loaded successfully")
        
        # Load model
        model = Sam3Model.from_pretrained(config.model_path)
        model = model.to(device)
        model.eval()  # Set to evaluation mode
        
        logger.info(f"Model loaded successfully on device: {device}")
        
        return model, processor, device
        
    except Exception as e:
        error_msg = f"Failed to load SAM 3 model: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ModelLoadError(error_msg) from e
