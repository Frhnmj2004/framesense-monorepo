"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import Header from "@/components/Header";
import VideoPlayer, { type SegmentationResult } from "@/components/VideoPlayer";
import UploadPanel from "@/components/UploadPanel";
import PromptPanel from "@/components/PromptPanel";
import StatusPanel, { type ProcessingState } from "@/components/StatusPanel";
import StatsPanel from "@/components/StatsPanel";
import ObjectList from "@/components/ObjectList";
import {
  uploadVideo,
  runSegmentation,
  getJobStatus,
} from "@/lib/api";

const POLL_INTERVAL_MS = 5000;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

export default function DashboardPage() {
  const [videoId, setVideoId] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [detections, setDetections] = useState<SegmentationResult | null>(null);
  const [processingState, setProcessingState] = useState<ProcessingState>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [highlightedObjectId, setHighlightedObjectId] = useState<number | null>(null);
  const [lastPrompt, setLastPrompt] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleFileSelect = useCallback(async (file: File) => {
    setFileName(file.name);
    setError(null);
    setProcessingState("uploading");
    setUploadProgress(0);
    try {
      const data = await uploadVideo(file, undefined, (p) => setUploadProgress(p));
      setVideoId(data.id);
      setVideoUrl(data.presigned_url);
      setUploadProgress(100);
      setProcessingState("idle");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setProcessingState("error");
    }
  }, []);

  const handleRunAnalysis = useCallback(
    async (prompt: string) => {
      if (!videoId) return;
      setError(null);
      setLastPrompt(prompt);
      setProcessingState("processing");
      try {
        const data = await runSegmentation({
          videoId,
          prompt,
          mode: "async",
        });
        if ("status" in data && data.status === "queued") {
          setJobId(data.job_id);
        } else if ("result" in data) {
          setDetections(data.result);
          setProcessingState("completed");
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Analysis failed");
        setProcessingState("error");
      }
    },
    [videoId]
  );

  useEffect(() => {
    if (!jobId || processingState !== "processing") return;

    const start = Date.now();

    const poll = async () => {
      if (Date.now() - start > POLL_TIMEOUT_MS) {
        setError("Analysis timed out");
        setProcessingState("error");
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        return;
      }
      try {
        const job = await getJobStatus(jobId);
        if (job.status === "completed" && job.result_json) {
          setDetections(job.result_json);
          setProcessingState("completed");
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
        } else if (job.status === "failed") {
          setError("Analysis failed");
          setProcessingState("error");
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Poll failed");
        setProcessingState("error");
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      }
    };

    pollIntervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
    poll();

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [jobId, processingState]);

  const framesProcessed = detections?.frames_processed ?? null;
  const resolution = detections
    ? { width: detections.video_width, height: detections.video_height }
    : null;
  const objectsDetected = detections
    ? new Set(
        detections.detections.flatMap((d) => d.objects.map((o) => o.object_id))
      ).size
    : null;

  const progressPercent =
    processingState === "processing"
      ? 50
      : processingState === "uploading"
        ? uploadProgress
        : 0;
  const stepLabel =
    processingState === "processing" ? "Processing…" : undefined;

  return (
    <>
      <Header />
      <main className="pt-32 pb-12 px-6 max-w-7xl mx-auto">
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 lg:col-span-8 glass-card rounded-2xl overflow-hidden shadow-xl p-4 flex flex-col gap-4">
            <VideoPlayer
              videoUrl={videoUrl}
              detections={detections}
              currentTime={currentTime}
              onTimeUpdate={setCurrentTime}
              highlightedObjectId={highlightedObjectId}
            />
          </div>
          <div className="col-span-12 lg:col-span-4">
            <ObjectList
              detections={detections}
              prompt={lastPrompt}
              highlightedObjectId={highlightedObjectId}
              onSelectObject={setHighlightedObjectId}
            />
          </div>

          <div className="col-span-12 md:col-span-6 lg:col-span-3">
            <UploadPanel
              fileName={fileName}
              uploadProgress={uploadProgress}
              isUploading={processingState === "uploading"}
              onFileSelect={handleFileSelect}
            />
          </div>
          <div className="col-span-12 md:col-span-6 lg:col-span-6">
            <PromptPanel
              disabled={!videoId || processingState === "uploading" || processingState === "processing"}
              onRunAnalysis={handleRunAnalysis}
            />
          </div>
          <div className="col-span-12 lg:col-span-3">
            <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
            {processingState === "error" && error && `Error: ${error}`}
            {processingState === "completed" && "Analysis completed."}
          </div>
          <StatusPanel
            state={processingState}
            progressPercent={progressPercent}
            stepLabel={stepLabel}
            errorMessage={error}
          />
          </div>

          <StatsPanel
            framesProcessed={framesProcessed}
            resolution={resolution}
            objectsDetected={objectsDetected}
          />
        </div>
      </main>
      <div
        className="fixed top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/10 blur-[120px] rounded-full -z-10"
        aria-hidden
      />
      <div
        className="fixed bottom-[-5%] right-[-5%] w-[30%] h-[30%] bg-primary/5 blur-[100px] rounded-full -z-10"
        aria-hidden
      />
    </>
  );
}
