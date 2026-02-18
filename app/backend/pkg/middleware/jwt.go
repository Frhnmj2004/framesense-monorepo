package middleware

import (
	"strings"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
)

// JWTConfig holds configuration for JWT middleware
type JWTConfig struct {
	Secret string
}

// Claims represents JWT claims
type Claims struct {
	UserID string `json:"user_id"`
	Role   string `json:"role"`
	jwt.RegisteredClaims
}

// JWTMiddleware creates a JWT authentication middleware
func JWTMiddleware(cfg JWTConfig) fiber.Handler {
	return func(ctx *fiber.Ctx) error {
		// Get Authorization header
		authHeader := ctx.Get("Authorization")
		if authHeader == "" {
			return ctx.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"success": false,
				"error":   "Authorization header is required",
			})
		}

		// Extract token from "Bearer <token>"
		parts := strings.Split(authHeader, " ")
		if len(parts) != 2 || parts[0] != "Bearer" {
			return ctx.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"success": false,
				"error":   "Invalid authorization header format",
			})
		}

		tokenString := parts[1]

		// Parse and validate token
		token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(token *jwt.Token) (interface{}, error) {
			// Validate signing method
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fiber.NewError(fiber.StatusUnauthorized, "Invalid signing method")
			}
			return []byte(cfg.Secret), nil
		})

		if err != nil {
			return ctx.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"success": false,
				"error":   "Invalid or expired token",
			})
		}

		// Extract claims
		claims, ok := token.Claims.(*Claims)
		if !ok || !token.Valid {
			return ctx.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"success": false,
				"error":   "Invalid token claims",
			})
		}

		// Attach user info to context
		ctx.Locals("user_id", claims.UserID)
		ctx.Locals("role", claims.Role)

		return ctx.Next()
	}
}

// GetUserID extracts user ID from context
func GetUserID(ctx *fiber.Ctx) string {
	if userID, ok := ctx.Locals("user_id").(string); ok {
		return userID
	}
	return ""
}

// GetRole extracts role from context
func GetRole(ctx *fiber.Ctx) string {
	if role, ok := ctx.Locals("role").(string); ok {
		return role
	}
	return ""
}
