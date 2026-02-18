package database

import (
	"fmt"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// Database interface for database operations
type Database interface {
	GetDB() *gorm.DB
	Close() error
}

// database implements the Database interface
type database struct {
	db *gorm.DB
}

// DatabaseConfig holds configuration for database connection
type DatabaseConfig struct {
	ConnectionString string
	LogLevel         logger.LogLevel
}

// NewDatabase creates a new database connection
func NewDatabase(cfg DatabaseConfig) (Database, error) {
	db, err := gorm.Open(postgres.Open(cfg.ConnectionString), &gorm.Config{
		Logger: logger.Default.LogMode(cfg.LogLevel),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}

	return &database{db: db}, nil
}

// GetDB returns the underlying GORM database instance
func (d *database) GetDB() *gorm.DB {
	return d.db
}

// Close closes the database connection
func (d *database) Close() error {
	sqlDB, err := d.db.DB()
	if err != nil {
		return fmt.Errorf("failed to get database instance: %w", err)
	}
	return sqlDB.Close()
}
