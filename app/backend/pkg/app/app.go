package app

import (
	"fmt"

	"github.com/Frhnmj2004/framesense-monorepo/app/backend/api/routes"
	"github.com/Frhnmj2004/framesense-monorepo/app/backend/config"
	"github.com/Frhnmj2004/framesense-monorepo/app/backend/internal/video"
	"github.com/Frhnmj2004/framesense-monorepo/app/backend/pkg/database"
	applogger "github.com/Frhnmj2004/framesense-monorepo/app/backend/pkg/logger"
	"github.com/Frhnmj2004/framesense-monorepo/app/backend/pkg/storage"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"gorm.io/gorm/logger"
)

// App represents the application container
type App struct {
	cfg        *config.Config
	logger     applogger.Logger
	db         database.Database
	storage    storage.Storage
	fiberApp   *fiber.App
	videoRepo  video.Repository
	videoSvc   video.Service
}

// NewApp creates a new application instance with dependency injection
func NewApp(cfg *config.Config) (*App, error) {
	app := &App{
		cfg: cfg,
	}

	// Initialize logger
	app.logger = applogger.NewLogger(applogger.LoggerConfig{
		EnableDebug: cfg.Environment == "development",
	})

	// Initialize database
	dbConfig := database.DatabaseConfig{
		ConnectionString: cfg.GetDBConnectionString(),
		LogLevel:         logger.Info,
	}
	if cfg.Environment == "development" {
		dbConfig.LogLevel = logger.Info
	} else {
		dbConfig.LogLevel = logger.Error
	}

	db, err := database.NewDatabase(dbConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize database: %w", err)
	}
	app.db = db

	// Run migrations
	app.videoRepo = video.NewRepository(db)
	if err := app.videoRepo.CreateTables(); err != nil {
		return nil, fmt.Errorf("failed to create tables: %w", err)
	}

	// Initialize storage (S3)
	storageConfig := storage.Config{
		Region:          cfg.S3Region,
		Bucket:          cfg.S3Bucket,
		AccessKeyID:     cfg.S3AccessKeyID,
		SecretAccessKey: cfg.S3SecretAccessKey,
		Endpoint:        cfg.S3Endpoint,
	}
	storage, err := storage.NewS3Storage(storageConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize storage: %w", err)
	}
	app.storage = storage

	// Initialize services
	videoServiceConfig := video.ServiceConfig{}
	app.videoSvc = video.NewService(app.videoRepo, videoServiceConfig)

	// Initialize Fiber app
	app.fiberApp = fiber.New(fiber.Config{
		AppName: "Video Annotation Platform API",
	})

	// Register middleware
	app.registerMiddleware()

	// Register routes
	routes.RegisterRoutes(app.fiberApp, app.videoSvc)

	return app, nil
}

// registerMiddleware registers all application middleware
func (a *App) registerMiddleware() {
	// Recovery middleware
	a.fiberApp.Use(recover.New())

	// CORS middleware
	a.fiberApp.Use(cors.New(cors.Config{
		AllowOrigins: "*",
		AllowMethods: "GET,POST,PUT,DELETE,OPTIONS",
		AllowHeaders: "Origin,Content-Type,Accept,Authorization",
	}))

	// JWT middleware (applied to protected routes via route groups)
	// Note: In Phase 1, we're not applying JWT middleware globally
	// It will be applied selectively in Phase 2 when auth endpoints are added
}

// Start starts the HTTP server
func (a *App) Start() error {
	addr := ":" + a.cfg.ServerPort
	a.logger.Info(fmt.Sprintf("Starting server on %s", addr))
	return a.fiberApp.Listen(addr)
}

// Shutdown gracefully shuts down the application
func (a *App) Shutdown() error {
	if err := a.db.Close(); err != nil {
		return fmt.Errorf("failed to close database: %w", err)
	}
	return nil
}
