package routes

import (
	"github.com/Frhnmj2004/framesense-monorepo/app/backend/api/controllers"
	"github.com/Frhnmj2004/framesense-monorepo/app/backend/internal/video"
	"github.com/gofiber/fiber/v2"
	fiberSwagger "github.com/swaggo/fiber-swagger"
)

// RegisterRoutes registers all application routes
func RegisterRoutes(app *fiber.App, videoService video.Service) {
	// Swagger documentation route
	app.Get("/swagger/*", fiberSwagger.WrapHandler)

	// Initialize controllers
	healthController := controllers.NewHealthController()
	videoController := controllers.NewVideoController(videoService)

	// Health check route (no auth required)
	app.Get("/health", healthController.HealthCheck)

	// Video routes
	api := app.Group("/videos")
	api.Post("", videoController.CreateVideo)
	api.Get("", videoController.GetAllVideos)
	api.Get("/:id", videoController.GetVideo)
}
