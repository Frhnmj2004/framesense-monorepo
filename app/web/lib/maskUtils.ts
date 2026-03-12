export type RleSize = [number, number];

export type RleMask = {
  counts: string;
  size: number[];
};

/**
 * Decode COCO-style uncompressed RLE into a flat binary mask.
 *
 * - counts: space-separated run lengths, starting with background (0) runs
 * - size: [height, width]
 * - order: Fortran/column-major (x varies slowest, y fastest)
 */
export function decodeCocoRle(counts: string, size: RleSize): Uint8Array {
  const [height, width] = size;
  const total = height * width;

  if (!counts || total === 0) {
    return new Uint8Array(total);
  }

  const runs = counts
    .trim()
    .split(/\s+/)
    .map((v) => Number(v))
    .filter((v) => Number.isFinite(v) && v >= 0);

  const mask = new Uint8Array(total);
  let value = 0; // start with background
  let idx = 0;

  for (const run of runs) {
    const end = Math.min(idx + run, total);
    if (value === 1) {
      for (let i = idx; i < end; i++) {
        mask[i] = 1;
      }
    }
    idx = end;
    value = value === 0 ? 1 : 0;
    if (idx >= total) break;
  }

  return mask;
}

/**
 * Convert a flat column-major binary mask into ImageData with RGBA fill.
 *
 * - decoded: Uint8Array of length H*W, in column-major order
 * - size: [height, width]
 * - fillRgba: color + alpha (0–1) for foreground pixels
 */
export function createMaskImageData(
  decoded: Uint8Array,
  size: RleSize,
  fillRgba: { r: number; g: number; b: number; a: number }
): ImageData {
  const [height, width] = size;
  const imageData = new ImageData(width, height);
  const data = imageData.data;

  const alpha = Math.max(0, Math.min(1, fillRgba.a)) * 255;

  // Column-major source -> row-major ImageData
  for (let x = 0; x < width; x++) {
    for (let y = 0; y < height; y++) {
      const srcIndex = x * height + y;
      if (decoded[srcIndex] !== 1) continue;

      const dstIndex = (y * width + x) * 4;
      data[dstIndex] = fillRgba.r;
      data[dstIndex + 1] = fillRgba.g;
      data[dstIndex + 2] = fillRgba.b;
      data[dstIndex + 3] = alpha;
    }
  }

  return imageData;
}

