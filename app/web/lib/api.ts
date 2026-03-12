const getBaseUrl = () => {
  const url = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (!url) throw new Error("NEXT_PUBLIC_BACKEND_URL is not set");
  return url.replace(/\/$/, "");
};

export type UploadResponse = {
  id: string;
  title: string | null;
  s3_key: string;
  presigned_url: string;
  uploaded_at: string;
};

export type SegmentResponseSync = {
  job_id: string;
  result: {
    session_id: string;
    frames_processed: number;
    video_width: number;
    video_height: number;
    detections: Array<{
      frame_index: number;
      objects: Array<{
        object_id: number;
        score: number;
        box: [number, number, number, number];
        mask_rle?: { counts: string; size: number[] };
      }>;
    }>;
  };
};

export type SegmentResponseAsync = {
  job_id: string;
  status: string;
};

export type JobStatusResponse = {
  job_id: string;
  video_id: string;
  prompt: string;
  status: "queued" | "completed" | "failed";
  result_json: SegmentResponseSync["result"] | null;
  created_at: string;
  updated_at: string;
};

export async function uploadVideo(
  file: File,
  title?: string,
  onProgress?: (percent: number) => void
): Promise<UploadResponse> {
  const base = getBaseUrl();
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const json = JSON.parse(xhr.responseText);
          if (json.success && json.data) resolve(json.data as UploadResponse);
          else reject(new Error(json.message ?? "Upload failed"));
        } catch {
          reject(new Error("Invalid response"));
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err.message ?? `Upload failed: ${xhr.status}`));
        } catch {
          reject(new Error(`Upload failed: ${xhr.status}`));
        }
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error")));
    xhr.open("POST", `${base}/videos`);
    xhr.send(form);
  });
}

export async function runSegmentation(params: {
  videoId: string;
  prompt: string;
  mode: "sync" | "async";
  config?: { max_frame_count?: number };
}): Promise<SegmentResponseSync | SegmentResponseAsync> {
  const base = getBaseUrl();
  const res = await fetch(`${base}/segment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      videoId: params.videoId,
      prompt: params.prompt,
      mode: params.mode,
      config: params.config,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { message?: string }).message ?? `Segment failed: ${res.status}`);
  }

  const json = await res.json();
  if (!json.success || !json.data) throw new Error("Invalid response");
  return json.data as SegmentResponseSync | SegmentResponseAsync;
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const base = getBaseUrl();
  const res = await fetch(`${base}/jobs/${jobId}`);

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { message?: string }).message ?? `Job status failed: ${res.status}`);
  }

  const json = await res.json();
  if (!json.success || !json.data) throw new Error("Invalid response");
  return json.data as JobStatusResponse;
}
