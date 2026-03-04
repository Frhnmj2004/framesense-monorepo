"""SAM 3 video inference service wrapper."""

import logging
import time
from typing import Any

import numpy as np
import torch
from config import settings
from schemas import FrameDetection, VideoProcessResponse

logger = logging.getLogger(__name__)


class SamService:
    """Service wrapper for SAM 3 video predictor."""

    def __init__(self):
        """Initialize the SAM service."""
        self.predictor: Any | None = None
        self.device = settings.model_device

    def load_model(self) -> None:
        """
        Load the SAM 3 video predictor model.

        This should be called once at application startup.
        The model will be loaded on the specified device (default: cuda).
        """
        if self.predictor is not None:
            logger.warning("Model already loaded, skipping reload")
            return

        logger.info(f"Loading SAM 3 video predictor on device: {self.device}")

        # Determine device
        if self.device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU")
            self.device = "cpu"

        try:
            from sam3.model_builder import build_sam3_video_predictor

            self.predictor = build_sam3_video_predictor()

            # SAM 3 explicitly casts backbone FPN features to bfloat16 (sam3_image.py)
            # before feeding them to conv_s0/conv_s1 in the tracker's mask decoder.
            # The model weights default to float32, causing a dtype mismatch:
            #   "Input type (c10::BFloat16) and bias type (float) should be the same"
            # Converting the whole model to bfloat16 aligns weight dtypes with the
            # intentional bfloat16 intermediate tensors.
            if self.device == "cuda" and torch.cuda.is_bf16_supported():
                logger.info("Converting SAM 3 model to bfloat16 for dtype consistency")
                self.predictor.model = self.predictor.model.to(torch.bfloat16)

            logger.info("SAM 3 video predictor loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load SAM 3 model: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load SAM 3 model: {e}") from e

    def process_video(
        self,
        video_path: str,
        text_prompt: str,
        max_frames: int | None = None,
    ) -> VideoProcessResponse:
        """
        Process a video with SAM 3 using a text prompt.

        Args:
            video_path: Path to the video file (MP4 or directory of JPEG frames)
            text_prompt: Text description of objects to detect
            max_frames: Optional cap on frames to process (reduces memory for long videos)

        Returns:
            VideoProcessResponse with detection results for all frames

        Raises:
            RuntimeError: If model is not loaded or inference fails
        """
        if self.predictor is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        session_id: str | None = None
        step_start = time.perf_counter()

        try:
            # Step 1: Start a new session
            logger.info("[sam_service] start_session | path=%s", video_path)
            start_response = self.predictor.handle_request(
                request={
                    "type": "start_session",
                    "resource_path": str(video_path),
                }
            )
            session_id = start_response["session_id"]
            logger.info(
                "[sam_service] session started | session_id=%s | elapsed=%.1fs",
                session_id,
                time.perf_counter() - step_start,
            )

            # Step 2: Add text prompt on frame 0
            t_prompt = time.perf_counter()
            logger.info("[sam_service] add_prompt | frame=0 | text=%s", text_prompt[:40])
            add_prompt_response = self.predictor.handle_request(
                request={
                    "type": "add_prompt",
                    "session_id": session_id,
                    "frame_index": 0,
                    "text": text_prompt,
                }
            )

            # Get initial frame detection (frame 0)
            initial_outputs = add_prompt_response["outputs"]
            initial_frame_idx = add_prompt_response["frame_index"]

            # Get video dimensions from first frame's mask shape
            # If no masks, we'll get dimensions from propagated frames
            video_height, video_width = 1080, 1920  # Default fallback
            if len(initial_outputs["out_binary_masks"]) > 0:
                mask_shape = initial_outputs["out_binary_masks"][0].shape
                video_height, video_width = mask_shape[0], mask_shape[1]

            # Collect detections from all frames
            detections: list[FrameDetection] = []
            processed_frame_indices: set[int] = set()

            # Process initial frame (frame 0) - always include it even if empty
            detection = self._process_frame_outputs(
                initial_outputs,
                initial_frame_idx,
                video_width,
                video_height,
            )
            detections.append(detection)
            processed_frame_indices.add(initial_frame_idx)
            logger.info(
                "[sam_service] add_prompt done | elapsed=%.1fs",
                time.perf_counter() - t_prompt,
            )

            # Step 3: Propagate detections through the entire video
            t_propagate = time.perf_counter()
            logger.info("[sam_service] propagate start | max_frame_num_to_track=%s", max_frames)
            frame_count = 0
            log_interval = 10  # log every N frames

            # Use handle_stream_request for propagation
            for frame_result in self.predictor.handle_stream_request(
                request={
                    "type": "propagate_in_video",
                    "session_id": session_id,
                    "propagation_direction": "both",  # Forward and backward from frame 0
                    "start_frame_index": 0,
                    "max_frame_num_to_track": max_frames,  # None = all frames
                }
            ):
                frame_idx = frame_result["frame_index"]
                outputs = frame_result["outputs"]

                # Skip frame 0 as we already processed it
                if frame_idx in processed_frame_indices:
                    continue

                frame_count += 1
                if frame_count % log_interval == 0 or frame_count == 1:
                    elapsed = time.perf_counter() - t_propagate
                    logger.info(
                        "[sam_service] propagate progress | frame=%s | frames_so_far=%s | elapsed=%.1fs",
                        frame_idx,
                        frame_count,
                        elapsed,
                    )

                # Update video dimensions from first non-empty frame
                if len(outputs["out_binary_masks"]) > 0:
                    mask_shape = outputs["out_binary_masks"][0].shape
                    video_height, video_width = mask_shape[0], mask_shape[1]

                # Process this frame's outputs (include even if empty)
                detection = self._process_frame_outputs(
                    outputs,
                    frame_idx,
                    video_width,
                    video_height,
                )
                detections.append(detection)
                processed_frame_indices.add(frame_idx)

            # Sort detections by frame index
            detections.sort(key=lambda x: x.frame_index)
            elapsed_propagate = time.perf_counter() - t_propagate
            logger.info(
                "[sam_service] propagate done | total_frames=%s | elapsed=%.1fs",
                len(detections),
                elapsed_propagate,
            )

            return VideoProcessResponse(
                session_id=session_id,
                frames_processed=len(detections),
                detections=detections,
            )

        except Exception as e:
            logger.error(f"Error processing video: {e}", exc_info=True)
            raise RuntimeError(f"Video processing failed: {e}") from e

        finally:
            # Step 4: Always close the session to free GPU memory
            if session_id is not None:
                try:
                    logger.debug(f"Closing session: {session_id}")
                    self.predictor.handle_request(
                        request={
                            "type": "close_session",
                            "session_id": session_id,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error closing session {session_id}: {e}")

    def _process_frame_outputs(
        self,
        outputs: dict[str, np.ndarray],
        frame_idx: int,
        video_width: int,
        video_height: int,
    ) -> FrameDetection:
        """
        Process SAM 3 frame outputs into FrameDetection format.

        Args:
            outputs: SAM 3 outputs dict with out_obj_ids, out_probs, out_boxes_xywh, out_binary_masks
            frame_idx: Frame index
            video_width: Video width in pixels
            video_height: Video height in pixels

        Returns:
            FrameDetection with converted boxes and scores
        """
        obj_ids = outputs["out_obj_ids"]
        probs = outputs["out_probs"]
        boxes_xywh = outputs["out_binary_masks"]  # We'll compute boxes from masks

        # Get mask shape from first mask
        if len(outputs["out_binary_masks"]) > 0:
            mask_shape = outputs["out_binary_masks"][0].shape
        else:
            mask_shape = [video_height, video_width]

        # Convert normalized xywh boxes to absolute xyxy coordinates
        # SAM 3 provides out_boxes_xywh in normalized format [x, y, w, h] (0-1 range)
        # We need to convert to absolute [x1, y1, x2, y2] in pixels
        boxes_xyxy: list[list[float]] = []

        if "out_boxes_xywh" in outputs and len(outputs["out_boxes_xywh"]) > 0:
            boxes_xywh_normalized = outputs["out_boxes_xywh"]
            for box in boxes_xywh_normalized:
                # Convert from normalized [x, y, w, h] to absolute [x1, y1, x2, y2]
                x_norm, y_norm, w_norm, h_norm = box
                x1 = x_norm * video_width
                y1 = y_norm * video_height
                x2 = (x_norm + w_norm) * video_width
                y2 = (y_norm + h_norm) * video_height
                boxes_xyxy.append([float(x1), float(y1), float(x2), float(y2)])
        elif len(outputs["out_binary_masks"]) > 0:
            # Fallback: compute boxes from masks if out_boxes_xywh not available
            for mask in outputs["out_binary_masks"]:
                # Find bounding box from mask
                rows = np.any(mask, axis=1)
                cols = np.any(mask, axis=0)
                if rows.any() and cols.any():
                    y_min, y_max = np.where(rows)[0][[0, -1]]
                    x_min, x_max = np.where(cols)[0][[0, -1]]
                    boxes_xyxy.append(
                        [
                            float(x_min),
                            float(y_min),
                            float(x_max + 1),
                            float(y_max + 1),
                        ]
                    )
                else:
                    # Empty mask - skip or add empty box
                    boxes_xyxy.append([0.0, 0.0, 0.0, 0.0])

        # Convert scores to list
        scores_list = [float(score) for score in probs]

        return FrameDetection(
            frame_index=int(frame_idx),
            boxes=boxes_xyxy,
            scores=scores_list,
            mask_shape=[int(mask_shape[0]), int(mask_shape[1])],
        )

    def shutdown(self) -> None:
        """Shutdown the SAM service and free resources."""
        if self.predictor is not None:
            try:
                logger.info("Shutting down SAM 3 predictor")
                self.predictor.shutdown()
            except Exception as e:
                logger.warning(f"Error during predictor shutdown: {e}")
            finally:
                self.predictor = None
