"use client";

import { useEffect, useRef } from "react";
import type { SegmentationResult } from "./VideoPlayer";

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
  const { video_width, video_height, detections: frames } = detections;

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    const video = videoRef.current;
    if (!canvas || !container || !video) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

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
  }, [detections, currentTime, video_width, video_height, frames, highlightedObjectId, containerRef, videoRef]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ left: 0, top: 0 }}
      aria-hidden
    />
  );
}
