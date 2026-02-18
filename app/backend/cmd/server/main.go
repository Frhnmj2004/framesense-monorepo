package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/Frhnmj2004/framesense-monorepo/app/backend/config"
	_ "github.com/Frhnmj2004/framesense-monorepo/app/backend/docs" // swagger docs
	"github.com/Frhnmj2004/framesense-monorepo/app/backend/pkg/app"
)

// @title Video Annotation Platform API
// @version 1.0
// @description API for Video Annotation Platform - Phase 1 Foundation
// @termsOfService http://swagger.io/terms/

// @contact.name API Support
// @contact.email support@example.com

// @license.name Apache 2.0
// @license.url http://www.apache.org/licenses/LICENSE-2.0.html

// @host localhost:8080
// @BasePath /
// @schemes http https

// @securityDefinitions.apikey BearerAuth
// @in header
// @name Authorization
// @description Type "Bearer" followed by a space and JWT token.

func main() {
	// Load configuration
	cfg := config.Load()

	// Create application instance
	application, err := app.NewApp(cfg)
	if err != nil {
		log.Fatalf("Failed to create app: %v", err)
	}

	// Setup graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	// Start server in a goroutine
	go func() {
		if err := application.Start(); err != nil {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal
	<-sigChan
	log.Println("Shutting down server...")

	// Graceful shutdown
	if err := application.Shutdown(); err != nil {
		log.Printf("Error during shutdown: %v", err)
	}

	log.Println("Server stopped")
}
