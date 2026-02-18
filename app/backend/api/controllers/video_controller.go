package controllers

import (
	"github.com/Frhnmj2004/framesense-monorepo/app/backend/internal/video"
	"github.com/Frhnmj2004/framesense-monorepo/app/backend/types"
	"github.com/gofiber/fiber/v2"
)

// VideoController handles video-related endpoints
type VideoController struct {
	videoService video.Service
}

// NewVideoController creates a new video controller
func NewVideoController(videoService video.Service) *VideoController {
	return &VideoController{
		videoService: videoService,
	}
}

// CreateVideo handles POST /videos
// @Summary Create video metadata
// @Description Creates a new video metadata record
// @Tags videos
// @Accept json
// @Produce json
// @Param video body types.CreateVideoRequest true "Video metadata"
// @Success 201 {object} types.SuccessResponse{data=types.VideoResponse}
// @Failure 400 {object} types.ErrorResponse
// @Failure 500 {object} types.ErrorResponse
// @Router /videos [post]
// @Security BearerAuth
func (c *VideoController) CreateVideo(ctx *fiber.Ctx) error {
	var req types.CreateVideoRequest

	if err := ctx.BodyParser(&req); err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(
			types.NewErrorResponse(err, "Invalid request body"),
		)
	}

	video, err := c.videoService.CreateVideo(&req)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(
			types.NewErrorResponse(err, "Failed to create video"),
		)
	}

	return ctx.Status(fiber.StatusCreated).JSON(types.NewSuccessResponse(video))
}

// GetVideo handles GET /videos/:id
// @Summary Get video by ID
// @Description Retrieves a video metadata by its ID
// @Tags videos
// @Accept json
// @Produce json
// @Param id path string true "Video ID"
// @Success 200 {object} types.SuccessResponse{data=types.VideoResponse}
// @Failure 404 {object} types.ErrorResponse
// @Failure 500 {object} types.ErrorResponse
// @Router /videos/{id} [get]
// @Security BearerAuth
func (c *VideoController) GetVideo(ctx *fiber.Ctx) error {
	id := ctx.Params("id")

	video, err := c.videoService.GetVideoByID(id)
	if err != nil {
		return ctx.Status(fiber.StatusNotFound).JSON(
			types.NewErrorResponse(err, "Video not found"),
		)
	}

	return ctx.JSON(types.NewSuccessResponse(video))
}

// GetAllVideos handles GET /videos
// @Summary Get all videos
// @Description Retrieves all video metadata records
// @Tags videos
// @Accept json
// @Produce json
// @Success 200 {object} types.SuccessResponse{data=[]types.VideoResponse}
// @Failure 500 {object} types.ErrorResponse
// @Router /videos [get]
// @Security BearerAuth
func (c *VideoController) GetAllVideos(ctx *fiber.Ctx) error {
	videos, err := c.videoService.GetAllVideos()
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(
			types.NewErrorResponse(err, "Failed to retrieve videos"),
		)
	}

	return ctx.JSON(types.NewSuccessResponse(videos))
}
