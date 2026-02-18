package video

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// Video represents the video metadata model
type Video struct {
	ID          string         `gorm:"type:uuid;primary_key;default:gen_random_uuid()" json:"id"`
	Title       string         `gorm:"not null" json:"title"`
	Description string         `gorm:"type:text" json:"description"`
	S3Key       string         `gorm:"not null" json:"s3_key"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
	DeletedAt   gorm.DeletedAt `gorm:"index" json:"deleted_at,omitempty"`
}

// TableName specifies the table name for Video model
func (Video) TableName() string {
	return "videos"
}

// BeforeCreate hook to generate UUID if not set
func (v *Video) BeforeCreate(tx *gorm.DB) error {
	if v.ID == "" {
		v.ID = uuid.New().String()
	}
	return nil
}
