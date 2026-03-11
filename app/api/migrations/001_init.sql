-- Videos table: stores metadata for uploaded videos
CREATE TABLE IF NOT EXISTS videos (
  id UUID PRIMARY KEY,
  title VARCHAR(500),
  s3_key TEXT NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_videos_status ON videos (status);
CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos (created_at DESC);
