package controllers

import (
	"github.com/Frhnmj2004/framesense-monorepo/app/backend/types"
	"github.com/gofiber/fiber/v2"
)

// HealthController handles health check endpoints
type HealthController struct{}

// NewHealthController creates a new health controller
func NewHealthController() *HealthController {
	return &HealthController{}
}

// HealthCheck handles GET /health
// @Summary Health check endpoint
// @Description Returns the health status of the API
// @Tags health
// @Accept json
// @Produce json
// @Success 200 {object} types.SuccessResponse
// @Router /health [get]
func (c *HealthController) HealthCheck(ctx *fiber.Ctx) error {
	return ctx.JSON(types.NewSuccessResponse("ok"))
}
