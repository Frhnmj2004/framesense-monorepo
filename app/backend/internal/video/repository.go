package video

import (
	"fmt"

	"github.com/Frhnmj2004/framesense-monorepo/app/backend/pkg/database"
)

// Repository interface for video data operations
type Repository interface {
	// CreateTables creates/migrates the video tables
	CreateTables() error

	// Create creates a new video record
	Create(video *Video) error

	// GetByID retrieves a video by ID
	GetByID(id string) (*Video, error)

	// GetAll retrieves all videos (excluding soft-deleted)
	GetAll() ([]*Video, error)
}

// repository implements the Repository interface
type repository struct {
	db database.Database
}

// NewRepository creates a new video repository
func NewRepository(db database.Database) Repository {
	return &repository{
		db: db,
	}
}

// CreateTables creates/migrates the video tables
func (r *repository) CreateTables() error {
	return r.db.GetDB().AutoMigrate(&Video{})
}

// Create creates a new video record
func (r *repository) Create(video *Video) error {
	if err := r.db.GetDB().Create(video).Error; err != nil {
		return fmt.Errorf("failed to create video: %w", err)
	}
	return nil
}

// GetByID retrieves a video by ID
func (r *repository) GetByID(id string) (*Video, error) {
	var video Video
	if err := r.db.GetDB().Where("id = ?", id).First(&video).Error; err != nil {
		return nil, fmt.Errorf("failed to get video by id %s: %w", id, err)
	}
	return &video, nil
}

// GetAll retrieves all videos (excluding soft-deleted)
func (r *repository) GetAll() ([]*Video, error) {
	var videos []*Video
	if err := r.db.GetDB().Find(&videos).Error; err != nil {
		return nil, fmt.Errorf("failed to get all videos: %w", err)
	}
	return videos, nil
}
