"""COCO-style RLE decoding utilities.

The inference service encodes binary masks using uncompressed COCO RLE in
column-major (Fortran) order via ``_mask_to_rle`` in ``sam_service.py``.

This module provides the inverse: convert the space-separated run-length
string back into a (H, W) boolean NumPy array.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


def decode_coco_rle(counts: str, size: Tuple[int, int]) -> np.ndarray:
    """Decode COCO-style uncompressed RLE into a (H, W) boolean mask.

    Args:
        counts: Space-separated run lengths, starting with background (0) runs.
        size: (height, width) of the mask.

    Returns:
        Boolean NumPy array of shape (height, width) with True for foreground.
    """
    height, width = size
    total = height * width

    if not counts or total == 0:
        return np.zeros((height, width), dtype=bool)

    runs = [
        int(v)
        for v in counts.strip().split()
        if v.strip() != ""
    ]

    flat = np.zeros(total, dtype=bool)
    idx = 0
    value = 0  # start with background

    for run in runs:
        end = min(idx + run, total)
        if value == 1:
            flat[idx:end] = True
        idx = end
        value = 1 - value
        if idx >= total:
            break

    # Column-major (Fortran) order to match _mask_to_rle
    return flat.reshape((height, width), order="F")

