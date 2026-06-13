"""Thin wrapper around the SAM-3D Objects inference API.

This module assumes that the `sam-3d-objects` repository is available locally
and that checkpoints have been downloaded as described in the README.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np

from config import settings

logger = logging.getLogger(__name__)


class Sam3DNotAvailable(RuntimeError):
    """Raised when SAM-3D is not configured or cannot be imported."""


def _get_repo_and_config() -> tuple[Path, Path]:
    repo = settings.sam3d_repo_path
    ckpt = settings.sam3d_checkpoint_path

    if not repo or not ckpt:
        raise Sam3DNotAvailable(
            "SAM-3D not configured. Set SAM3D_REPO_PATH and SAM3D_CHECKPOINT_PATH env vars."
        )

    repo_path = Path(repo)
    ckpt_dir = Path(ckpt)
    config_path = ckpt_dir / "pipeline.yaml"

    if not repo_path.exists():
        raise Sam3DNotAvailable(f"SAM-3D repo path does not exist: {repo_path}")
    if not config_path.exists():
        raise Sam3DNotAvailable(f"SAM-3D pipeline config not found at: {config_path}")

    return repo_path, config_path


def run_3d(
    image_path: Path,
    mask: np.ndarray,
    seed: Optional[int],
    preset: str,
    workdir: Path,
) -> dict:
    """Run SAM-3D Objects on a single image + mask.

    Returns a dict with at least:
      - ply_path: Path to Gaussian splat (.ply)
      - preview_path: Path to a preview image (currently a copy of input image)
      - glb_path: Optional Path to exported GLB mesh (if conversion succeeds)
    """
    repo_path, config_path = _get_repo_and_config()

    # Ensure mask is boolean
    mask_bool = mask.astype(bool)

    # Make sure notebook path is importable
    notebook_path = repo_path / "notebook"
    if str(notebook_path) not in sys.path:
        sys.path.append(str(notebook_path))

    try:
        from inference import Inference, load_image  # type: ignore
    except Exception as e:  # pragma: no cover - import-time failure
        raise Sam3DNotAvailable(f"Failed to import SAM-3D inference module: {e}") from e

    workdir.mkdir(parents=True, exist_ok=True)

    # Load image as expected by SAM-3D helpers
    image = load_image(str(image_path))

    logger.info("[sam3d_runner] loading SAM-3D pipeline | config=%s", config_path)
    inference = Inference(str(config_path), compile=(preset == "quality"))

    logger.info("[sam3d_runner] running inference | preset=%s", preset)
    output = inference(image, mask_bool, seed=seed)

    gs = output.get("gs")
    if gs is None or not hasattr(gs, "save_ply"):
        raise RuntimeError("SAM-3D output did not contain a valid 'gs' Gaussian splat")

    ply_path = workdir / "splat.ply"
    logger.info("[sam3d_runner] saving splat | path=%s", ply_path)
    gs.save_ply(str(ply_path))

    # Basic preview: reuse the original image as a static preview
    preview_path = workdir / "preview.png"
    try:
        from shutil import copyfile

        copyfile(image_path, preview_path)
    except Exception:
        preview_path = None  # best-effort only

    # Optional: convert PLY -> GLB for web viewing
    glb_path: Optional[Path] = None
    try:
        import trimesh  # type: ignore

        mesh = trimesh.load(str(ply_path))
        glb_path = workdir / "model.glb"
        mesh.export(str(glb_path))
    except Exception as e:  # pragma: no cover - optional path
        logger.warning("Failed to convert PLY to GLB: %s", e)
        glb_path = None

    return {
        "ply_path": ply_path,
        "preview_path": preview_path,
        "glb_path": glb_path,
    }

