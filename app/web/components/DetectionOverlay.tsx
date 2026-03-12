"use client";

import { useEffect, useRef } from "react";
import type { SegmentationResult } from "./VideoPlayer";
import { createMaskImageData, decodeCocoRle } from "../lib/maskUtils";

type DetectionOverlayProps = {
  detections: SegmentationResult;
  currentTime: number;
  containerRef: React.RefObject<HTMLDivElement | null>;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  highlightedObjectId?: number | null;
};

export default function DetectionOverlay({
  detections,
  currentTime,
  containerRef,
  videoRef,
  highlightedObjectId = null,
}: DetectionOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const maskCacheRef = useRef<Map<string, ImageData>>(new Map());
  const { video_width, video_height, detections: frames } = detections;

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    const video = videoRef.current;
    if (!canvas || !container || !video) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const maskCache = maskCacheRef.current;

    const updateSize = () => {
      const rect = container.getBoundingClientRect();
      if (rect.width !== canvas.width || rect.height !== canvas.height) {
        canvas.width = rect.width;
        canvas.height = rect.height;
      }
    };

    const draw = () => {
      updateSize();
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const scaleX = canvas.width / video_width;
      const scaleY = canvas.height / video_height;

      const fps = 30;
      const frameIndex = Math.floor(currentTime * fps);

      const frameData = frames.find((d) => d.frame_index === frameIndex);
      if (!frameData) return;

      // First pass: masks
      if (video_width > 0 && video_height > 0) {
        const offscreen = document.createElement("canvas");
        offscreen.width = video_width;
        offscreen.height = video_height;
        const offscreenCtx = offscreen.getContext("2d");

        if (offscreenCtx) {
          frameData.objects.forEach((obj) => {
            const rle = obj.mask_rle;
            if (!rle || !rle.counts || !Array.isArray(rle.size) || rle.size.length < 2) {
              return;
            }

            const key = `${frameIndex}-${obj.object_id}`;
            let imageData = maskCache.get(key);

            if (!imageData) {
              try {
                const [h, w] = rle.size as [number, number];
                const decoded = decodeCocoRle(rle.counts, [h, w]);
                imageData = createMaskImageData(decoded, [h, w], {
                  r: 118,
                  g: 169,
                  b: 57,
                  a: 0.4,
                });
                maskCache.set(key, imageData);
              } catch {
                return;
              }
            }

            offscreenCtx.clearRect(0, 0, offscreen.width, offscreen.height);
            offscreenCtx.putImageData(imageData, 0, 0);
            ctx.drawImage(
              offscreen,
              0,
              0,
              video_width,
              video_height,
              0,
              0,
              canvas.width,
              canvas.height
            );
          });
        }
      }

      // Second pass: boxes and labels
      frameData.objects.forEach((obj) => {
        const [x1, y1, x2, y2] = obj.box;
        const isHighlighted = highlightedObjectId === obj.object_id;
        ctx.strokeStyle = isHighlighted ? "#94c457" : "#76a939";
        ctx.lineWidth = isHighlighted ? 3 : 2;
        ctx.setLineDash(isHighlighted ? [6, 4] : []);
        const w = (x2 - x1) * scaleX;
        const h = (y2 - y1) * scaleY;
        ctx.strokeRect(x1 * scaleX, y1 * scaleY, w, h);
        ctx.font = "12px sans-serif";
        ctx.fillStyle = "#76a939";
        ctx.fillText(
          `${(obj.score * 100).toFixed(0)}%`,
          x1 * scaleX,
          y1 * scaleY - 4
        );
      });
    };

    draw();
  }, [
    detections,
    currentTime,
    video_width,
    video_height,
    frames,
    highlightedObjectId,
    containerRef,
    videoRef,
  ]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ left: 0, top: 0 }}
      aria-hidden
    />
  );
}
