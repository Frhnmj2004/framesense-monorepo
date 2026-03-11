-- Jobs table: segmentation jobs linked to videos
CREATE TABLE IF NOT EXISTS jobs (
  job_id UUID PRIMARY KEY,
  video_id UUID NOT NULL REFERENCES videos (id) ON DELETE CASCADE,
  prompt TEXT NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'queued',
  result_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_video_id ON jobs (video_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs (created_at DESC);
