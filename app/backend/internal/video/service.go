package video

import (
	"fmt"

	"github.com/Frhnmj2004/framesense-monorepo/app/backend/types"
)

// Service interface for video business logic
type Service interface {
	// CreateVideo creates a new video metadata
	CreateVideo(req *types.CreateVideoRequest) (*types.VideoResponse, error)

	// GetVideoByID retrieves a video by ID
	GetVideoByID(id string) (*types.VideoResponse, error)

	// GetAllVideos retrieves all videos
	GetAllVideos() ([]*types.VideoResponse, error)
}

// service implements the Service interface
type service struct {
	repo   Repository
	config ServiceConfig
}

// NewService creates a new video service
func NewService(repo Repository, cfg ServiceConfig) Service {
	return &service{
		repo:   repo,
		config: cfg,
	}
}

// CreateVideo creates a new video metadata
func (s *service) CreateVideo(req *types.CreateVideoRequest) (*types.VideoResponse, error) {
	// Validate request
	if req.Title == "" {
		return nil, fmt.Errorf("title is required")
	}
	if req.S3Key == "" {
		return nil, fmt.Errorf("s3_key is required")
	}

	// Create video model
	video := &Video{
		Title:       req.Title,
		Description: req.Description,
		S3Key:       req.S3Key,
	}

	// Save to database
	if err := s.repo.Create(video); err != nil {
		return nil, fmt.Errorf("failed to create video: %w", err)
	}

	// Convert to response DTO
	return s.toVideoResponse(video), nil
}

// GetVideoByID retrieves a video by ID
func (s *service) GetVideoByID(id string) (*types.VideoResponse, error) {
	video, err := s.repo.GetByID(id)
	if err != nil {
		return nil, fmt.Errorf("failed to get video: %w", err)
	}

	return s.toVideoResponse(video), nil
}

// GetAllVideos retrieves all videos
func (s *service) GetAllVideos() ([]*types.VideoResponse, error) {
	videos, err := s.repo.GetAll()
	if err != nil {
		return nil, fmt.Errorf("failed to get all videos: %w", err)
	}

	// Convert to response DTOs
	responses := make([]*types.VideoResponse, len(videos))
	for i := range videos {
		responses[i] = s.toVideoResponse(videos[i])
	}

	return responses, nil
}

// toVideoResponse converts a Video model to VideoResponse DTO
func (s *service) toVideoResponse(video *Video) *types.VideoResponse {
	return &types.VideoResponse{
		ID:          video.ID,
		Title:       video.Title,
		Description: video.Description,
		S3Key:       video.S3Key,
		CreatedAt:   video.CreatedAt,
		UpdatedAt:   video.UpdatedAt,
	}
}
