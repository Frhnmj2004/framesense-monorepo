package storage

// Storage interface for object storage operations
type Storage interface {
	// GetPresignedURL generates a presigned URL for uploading/downloading objects
	GetPresignedURL(key string) (string, error)

	// DeleteObject deletes an object from storage
	DeleteObject(key string) error
}
