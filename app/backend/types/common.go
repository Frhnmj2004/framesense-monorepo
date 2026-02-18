package types

// SuccessResponse represents a successful API response
type SuccessResponse struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data"`
}

// ErrorResponse represents an error API response
type ErrorResponse struct {
	Success bool   `json:"success"`
	Error   string `json:"error"`
	Message string `json:"message,omitempty"`
}

// NewSuccessResponse creates a new success response
func NewSuccessResponse(data interface{}) *SuccessResponse {
	return &SuccessResponse{
		Success: true,
		Data:    data,
	}
}

// NewErrorResponse creates a new error response
func NewErrorResponse(err error, message string) *ErrorResponse {
	errMsg := ""
	if err != nil {
		errMsg = err.Error()
	}
	return &ErrorResponse{
		Success: false,
		Error:   errMsg,
		Message: message,
	}
}
