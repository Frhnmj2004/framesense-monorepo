"use client";

import { useRef, useEffect, useCallback } from "react";
import DetectionOverlay from "./DetectionOverlay";

export type Detection = {
  frame_index: number;
  objects: Array<{
    object_id: number;
    score: number;
    box: [number, number, number, number];
    mask_rle?: { counts: string; size: number[] };
  }>;
};

export type SegmentationResult = {
  session_id: string;
  frames_processed: number;
  video_width: number;
  video_height: number;
  detections: Detection[];
};

type VideoPlayerProps = {
  videoUrl: string | null;
  detections: SegmentationResult | null;
  currentTime: number;
  onTimeUpdate?: (currentTime: number) => void;
  highlightedObjectId?: number | null;
};

export default function VideoPlayer({
  videoUrl,
  detections,
  currentTime,
  onTimeUpdate,
  highlightedObjectId = null,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleTimeUpdate = useCallback(() => {
    const video = videoRef.current;
    if (video && onTimeUpdate) onTimeUpdate(video.currentTime);
  }, [onTimeUpdate]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    video.addEventListener("timeupdate", handleTimeUpdate);
    return () => video.removeEventListener("timeupdate", handleTimeUpdate);
  }, [handleTimeUpdate]);

  if (!videoUrl) {
    return (
      <div className="relative aspect-video bg-black rounded-xl overflow-hidden border border-white/5 flex items-center justify-center">
        <p className="text-slate-500 text-sm">Upload a video to get started</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative aspect-video bg-black rounded-xl overflow-hidden border border-white/5 group">
      <video
        ref={videoRef}
        src={videoUrl}
        className="w-full h-full object-contain"
        controls
        playsInline
        onTimeUpdate={handleTimeUpdate}
      />
      {detections && (
        <DetectionOverlay
          detections={detections}
          currentTime={currentTime}
          containerRef={containerRef}
          videoRef={videoRef}
          highlightedObjectId={highlightedObjectId}
        />
      )}
    </div>
  );
}
