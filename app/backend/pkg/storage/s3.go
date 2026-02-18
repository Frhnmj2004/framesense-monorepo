package storage

import (
	"context"
	"fmt"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

// s3Storage implements the Storage interface using AWS S3
type s3Storage struct {
	client *s3.Client
	bucket string
}

// NewS3Storage creates a new S3 storage instance
func NewS3Storage(cfg Config) (Storage, error) {
	ctx := context.Background()

	// Build AWS config with custom credentials if provided
	var awsCfg aws.Config
	var err error

	if cfg.AccessKeyID != "" && cfg.SecretAccessKey != "" {
		// Use explicit credentials
		awsCfg = aws.Config{
			Region: cfg.Region,
			Credentials: credentials.NewStaticCredentialsProvider(
				cfg.AccessKeyID,
				cfg.SecretAccessKey,
				"",
			),
		}
	} else {
		// Try to load default config (from environment, IAM role, etc.)
		awsCfg, err = awsconfig.LoadDefaultConfig(ctx, awsconfig.WithRegion(cfg.Region))
		if err != nil {
			return nil, fmt.Errorf("failed to load AWS config: %w", err)
		}
	}

	// Create S3 client options
	clientOptions := []func(*s3.Options){}

	// Set custom endpoint if provided (for S3-compatible services)
	if cfg.Endpoint != "" {
		clientOptions = append(clientOptions, func(o *s3.Options) {
			o.BaseEndpoint = aws.String(cfg.Endpoint)
			o.UsePathStyle = true // Required for S3-compatible services
		})
	}

	client := s3.NewFromConfig(awsCfg, clientOptions...)

	return &s3Storage{
		client: client,
		bucket: cfg.Bucket,
	}, nil
}

// GetPresignedURL generates a presigned URL for uploading/downloading objects
// Note: In Phase 1, this is a placeholder. Actual presigned URL generation
// will be implemented in later phases when file uploads are needed.
func (s *s3Storage) GetPresignedURL(key string) (string, error) {
	// TODO: Implement presigned URL generation in Phase 2+
	// For now, return a placeholder
	return fmt.Sprintf("s3://%s/%s", s.bucket, key), nil
}

// DeleteObject deletes an object from S3 storage
func (s *s3Storage) DeleteObject(key string) error {
	ctx := context.Background()

	_, err := s.client.DeleteObject(ctx, &s3.DeleteObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
	})

	if err != nil {
		return fmt.Errorf("failed to delete object %s: %w", key, err)
	}

	return nil
}

