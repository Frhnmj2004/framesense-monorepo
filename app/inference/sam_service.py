"""SAM 3 video inference service wrapper."""

import logging
import time
from typing import Any

import numpy as np
import torch
from config import settings
from schemas import FrameDetection, MaskRLE, ObjectDetection, VideoProcessResponse

logger = logging.getLogger(__name__)


def _mask_to_rle(binary_mask: np.ndarray) -> dict[str, Any]:
    """
    Encode a binary mask (H, W) into COCO uncompressed RLE format.

    Fortran (column-major) order — the convention used by pycocotools/COCO/Detectron2.
    Vectorized with numpy for speed on large masks.
    """
    h, w = binary_mask.shape
    flat = binary_mask.flatten(order="F").astype(np.uint8)
    n = len(flat)

    if n == 0:
        return {"counts": [0], "size": [h, w]}

    # Find positions where value changes
    diff_positions = np.where(flat[1:] != flat[:-1])[0] + 1
    positions = np.concatenate(([0], diff_positions, [n]))
    runs = np.diff(positions).tolist()

    # COCO RLE starts with a 0-valued run
    if flat[0] == 1:
        runs.insert(0, 0)

    return {"counts": runs, "size": [h, w]}


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

            # SAM 3 internally casts tensors to bfloat16 (sam3_image.py:836) and
            # expects the model to run under torch.autocast so PyTorch automatically
            # handles dtype promotion between float32 weights and bfloat16 activations.
            # The demo inference path (add_prompt / propagate_in_video) is NOT decorated
            # with @torch.autocast, so we must wrap our calls ourselves.
            self._use_autocast = (
                self.device == "cuda" and torch.cuda.is_bf16_supported()
            )
            if self._use_autocast:
                logger.info("Will use bfloat16 autocast for inference (GPU supports bf16)")

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

        Returns pixel-level segmentation masks (RLE-encoded) and bounding boxes
        for every detected object in every frame.
        """
        if self.predictor is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        session_id: str | None = None
        step_start = time.perf_counter()
        autocast_ctx = (
            torch.autocast(device_type="cuda", dtype=torch.bfloat16)
            if self._use_autocast
            else torch.inference_mode()
        )

        try:
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

            t_prompt = time.perf_counter()
            logger.info("[sam_service] add_prompt | frame=0 | text=%s", text_prompt[:40])
            with autocast_ctx:
                add_prompt_response = self.predictor.handle_request(
                    request={
                        "type": "add_prompt",
                        "session_id": session_id,
                        "frame_index": 0,
                        "text": text_prompt,
                    }
                )

            initial_outputs = add_prompt_response["outputs"]
            initial_frame_idx = add_prompt_response["frame_index"]

            video_height, video_width = self._extract_video_dims(initial_outputs)

            detections: list[FrameDetection] = []
            processed_frame_indices: set[int] = set()

            detection = self._build_frame_detection(
                initial_outputs, initial_frame_idx, video_width, video_height,
            )
            detections.append(detection)
            processed_frame_indices.add(initial_frame_idx)
            logger.info(
                "[sam_service] add_prompt done | objects=%d | elapsed=%.1fs",
                len(detection.objects),
                time.perf_counter() - t_prompt,
            )

            t_propagate = time.perf_counter()
            logger.info("[sam_service] propagate start | max_frame_num_to_track=%s", max_frames)
            frame_count = 0
            log_interval = 10

            propagate_autocast = (
                torch.autocast(device_type="cuda", dtype=torch.bfloat16)
                if self._use_autocast
                else torch.inference_mode()
            )
            with propagate_autocast:
                for frame_result in self.predictor.handle_stream_request(
                    request={
                        "type": "propagate_in_video",
                        "session_id": session_id,
                        "propagation_direction": "both",
                        "start_frame_index": 0,
                        "max_frame_num_to_track": max_frames,
                    }
                ):
                    frame_idx = frame_result["frame_index"]
                    outputs = frame_result["outputs"]

                    if frame_idx in processed_frame_indices:
                        continue

                    frame_count += 1
                    if frame_count % log_interval == 0 or frame_count == 1:
                        elapsed = time.perf_counter() - t_propagate
                        logger.info(
                            "[sam_service] propagate progress | frame=%s | frames_so_far=%s | elapsed=%.1fs",
                            frame_idx, frame_count, elapsed,
                        )

                    h, w = self._extract_video_dims(outputs)
                    if h != 0:
                        video_height, video_width = h, w

                    detection = self._build_frame_detection(
                        outputs, frame_idx, video_width, video_height,
                    )
                    detections.append(detection)
                    processed_frame_indices.add(frame_idx)

            detections.sort(key=lambda x: x.frame_index)
            elapsed_propagate = time.perf_counter() - t_propagate
            logger.info(
                "[sam_service] propagate done | total_frames=%s | elapsed=%.1fs",
                len(detections), elapsed_propagate,
            )

            return VideoProcessResponse(
                session_id=session_id,
                frames_processed=len(detections),
                video_width=video_width,
                video_height=video_height,
                detections=detections,
            )

        except Exception as e:
            logger.error(f"Error processing video: {e}", exc_info=True)
            raise RuntimeError(f"Video processing failed: {e}") from e

        finally:
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

    @staticmethod
    def _extract_video_dims(outputs: dict[str, np.ndarray]) -> tuple[int, int]:
        masks = outputs["out_binary_masks"]
        if len(masks) > 0:
            return int(masks[0].shape[0]), int(masks[0].shape[1])
        return 0, 0

    def _build_frame_detection(
        self,
        outputs: dict[str, np.ndarray],
        frame_idx: int,
        video_width: int,
        video_height: int,
    ) -> FrameDetection:
        """Convert raw SAM 3 outputs into FrameDetection with RLE masks."""
        obj_ids = outputs["out_obj_ids"]
        probs = outputs["out_probs"]
        masks = outputs["out_binary_masks"]  # (N, H, W) bool
        boxes_xywh = outputs["out_boxes_xywh"]  # (N, 4) normalized

        objects: list[ObjectDetection] = []

        for i in range(len(obj_ids)):
            mask = masks[i]  # (H, W) bool
            rle = _mask_to_rle(mask)

            # Normalized xywh -> absolute xyxy
            if len(boxes_xywh) > i:
                x_n, y_n, w_n, h_n = boxes_xywh[i]
                box = [
                    float(x_n * video_width),
                    float(y_n * video_height),
                    float((x_n + w_n) * video_width),
                    float((y_n + h_n) * video_height),
                ]
            else:
                rows = np.any(mask, axis=1)
                cols = np.any(mask, axis=0)
                if rows.any() and cols.any():
                    y_min, y_max = np.where(rows)[0][[0, -1]]
                    x_min, x_max = np.where(cols)[0][[0, -1]]
                    box = [float(x_min), float(y_min), float(x_max + 1), float(y_max + 1)]
                else:
                    box = [0.0, 0.0, 0.0, 0.0]

            # RLE counts as space-separated string for compact JSON
            rle_str = " ".join(str(c) for c in rle["counts"])

            objects.append(ObjectDetection(
                object_id=int(obj_ids[i]),
                score=float(probs[i]),
                box=box,
                mask_rle=MaskRLE(counts=rle_str, size=rle["size"]),
            ))

        return FrameDetection(frame_index=int(frame_idx), objects=objects)

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
