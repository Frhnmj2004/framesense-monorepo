package types

import "time"

// CreateVideoRequest represents the request to create a video metadata
type CreateVideoRequest struct {
	Title       string `json:"title" validate:"required" example:"Sample Video"`
	Description string `json:"description" example:"This is a sample video description"`
	S3Key       string `json:"s3_key" validate:"required" example:"videos/sample-video.mp4"`
}

// VideoResponse represents the video metadata response
type VideoResponse struct {
	ID          string    `json:"id" example:"550e8400-e29b-41d4-a716-446655440000"`
	Title       string    `json:"title" example:"Sample Video"`
	Description string    `json:"description" example:"This is a sample video description"`
	S3Key       string    `json:"s3_key" example:"videos/sample-video.mp4"`
	CreatedAt   time.Time `json:"created_at" example:"2024-01-01T00:00:00Z"`
	UpdatedAt   time.Time `json:"updated_at" example:"2024-01-01T00:00:00Z"`
}
