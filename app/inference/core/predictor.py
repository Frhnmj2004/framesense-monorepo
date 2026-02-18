"""SAM 3 inference predictor with concurrency control and timeout."""
import asyncio
import base64
import io
import numpy as np
import torch
from PIL import Image
from typing import List, Optional, NamedTuple
from pycocotools import mask as mask_utils

from app.config import Config
from core.model_loader import Sam3Model, Sam3Processor
from infra.exceptions import InferenceError, InferenceTimeoutError
from infra.logging import get_logger

logger = get_logger(__name__)


class MaskResult(NamedTuple):
    """Mask result structure."""
    rle: str
    bbox: List[int]
    score: float


class Predictor:
    """SAM 3 predictor with concurrency control and timeout."""

    def __init__(
        self,
        model: Sam3Model,
        processor: Sam3Processor,
        device: str,
        config: Config
    ):
        """Initialize predictor.
        
        Args:
            model: Loaded SAM3Model
            processor: Loaded Sam3Processor
            device: Device string ('cuda' or 'cpu')
            config: Application configuration
        """
        self.model = model
        self.processor = processor
        self.device = device
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrency)
        logger.info(
            f"Predictor initialized with max_concurrency={config.max_concurrency}, "
            f"timeout={config.inference_timeout}s"
        )

    def _decode_base64_image(self, image_base64: str) -> Image.Image:
        """Decode base64 image string to PIL Image.
        
        Args:
            image_base64: Base64 encoded image string
            
        Returns:
            PIL Image object
            
        Raises:
            InferenceError: If decoding fails
        """
        try:
            # Remove data URL prefix if present
            if "," in image_base64:
                image_base64 = image_base64.split(",")[1]
            
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            return image
        except Exception as e:
            raise InferenceError(f"Failed to decode base64 image: {str(e)}") from e

    def _encode_mask_to_rle(self, mask: np.ndarray) -> str:
        """Encode binary mask to RLE (Run-Length Encoding) string.
        
        Args:
            mask: Binary mask array (H x W)
            
        Returns:
            RLE string
        """
        # Convert to uint8 if needed
        if mask.dtype != np.uint8:
            mask = (mask > 0.5).astype(np.uint8)
        
        # Encode using pycocotools
        rle = mask_utils.encode(np.asfortranarray(mask))
        if isinstance(rle['counts'], bytes):
            rle['counts'] = rle['counts'].decode('utf-8')
        return rle['counts']

    def _post_process_outputs(
        self,
        outputs,
        original_size: tuple,
        threshold: float = 0.5,
        mask_threshold: float = 0.5
    ) -> List[MaskResult]:
        """Post-process model outputs to extract masks, bboxes, and scores.
        
        Args:
            outputs: Model outputs from SAM3
            original_size: Original image size (height, width)
            threshold: Score threshold for filtering masks
            mask_threshold: Threshold for binarizing masks
            
        Returns:
            List of MaskResult objects
        """
        try:
            # Post-process using processor
            results = self.processor.post_process_instance_segmentation(
                outputs,
                threshold=threshold,
                mask_threshold=mask_threshold,
                target_sizes=[original_size]
            )[0]

            mask_results = []
            
            for i, (mask, score, label) in enumerate(zip(
                results['masks'],
                results['scores'],
                results['labels']
            )):
                # Convert mask to numpy array
                mask_array = mask.cpu().numpy().astype(np.uint8)
                
                # Calculate bounding box from mask
                rows = np.any(mask_array, axis=1)
                cols = np.any(mask_array, axis=0)
                if not rows.any() or not cols.any():
                    continue
                
                y_min, y_max = np.where(rows)[0][[0, -1]]
                x_min, x_max = np.where(cols)[0][[0, -1]]
                
                bbox = [int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min)]
                
                # Encode mask to RLE
                rle = self._encode_mask_to_rle(mask_array)
                
                mask_results.append(MaskResult(
                    rle=rle,
                    bbox=bbox,
                    score=float(score)
                ))
            
            return mask_results
            
        except Exception as e:
            raise InferenceError(f"Failed to post-process outputs: {str(e)}") from e

    def _predict_sync(
        self,
        image: Image.Image,
        prompt: Optional[str] = None
    ) -> List[MaskResult]:
        """Synchronous prediction (runs in thread pool).
        
        Args:
            image: PIL Image
            prompt: Optional text prompt
            
        Returns:
            List of MaskResult objects
        """
        try:
            # Prepare inputs
            if prompt:
                inputs = self.processor(images=image, text=prompt, return_tensors="pt")
            else:
                # No prompt - use automatic mask generation
                inputs = self.processor(images=image, return_tensors="pt")
            
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Run inference
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Post-process
            original_size = image.size[::-1]  # (height, width)
            mask_results = self._post_process_outputs(outputs, original_size)
            
            return mask_results
            
        except Exception as e:
            raise InferenceError(f"Inference failed: {str(e)}") from e

    async def segment_image(
        self,
        image_base64: str,
        prompt: Optional[str] = None
    ) -> List[MaskResult]:
        """Segment image with concurrency control and timeout.
        
        Args:
            image_base64: Base64 encoded image string
            prompt: Optional text prompt for segmentation
            
        Returns:
            List of MaskResult objects
            
        Raises:
            InferenceTimeoutError: If inference exceeds timeout
            InferenceError: If inference fails
        """
        async with self.semaphore:
            try:
                # Decode image
                image = self._decode_base64_image(image_base64)
                
                # Run inference in thread pool with timeout
                loop = asyncio.get_event_loop()
                mask_results = await asyncio.wait_for(
                    loop.run_in_executor(None, self._predict_sync, image, prompt),
                    timeout=self.config.inference_timeout
                )
                
                logger.info(f"Segmentation completed: {len(mask_results)} masks found")
                return mask_results
                
            except asyncio.TimeoutError:
                error_msg = f"Inference exceeded timeout of {self.config.inference_timeout}s"
                logger.error(error_msg)
                raise InferenceTimeoutError(error_msg)
            except InferenceError:
                raise
            except Exception as e:
                error_msg = f"Unexpected error during inference: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise InferenceError(error_msg) from e
