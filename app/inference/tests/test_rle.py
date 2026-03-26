import numpy as np

from utils.rle import decode_coco_rle
from sam_service import _mask_to_rle


def test_decode_coco_rle_roundtrip():
    mask = np.zeros((2, 2), dtype=bool)
    mask[0, 1] = True  # simple non-empty mask

    rle = _mask_to_rle(mask)
    counts_str = " ".join(str(c) for c in rle["counts"])

    decoded = decode_coco_rle(counts_str, (rle["size"][0], rle["size"][1]))

    assert decoded.shape == mask.shape
    assert np.array_equal(decoded, mask)

