package logger

import (
	"log"
	"os"
)

// Logger interface for logging operations
type Logger interface {
	Info(msg string)
	Error(msg string, err error)
	Warn(msg string)
	Debug(msg string)
}

// logger implements the Logger interface
type loggerImpl struct {
	infoLogger  *log.Logger
	errorLogger *log.Logger
	warnLogger  *log.Logger
	debugLogger *log.Logger
}

// LoggerConfig holds configuration for logger
type LoggerConfig struct {
	EnableDebug bool
}

// NewLogger creates a new logger instance
func NewLogger(cfg LoggerConfig) Logger {
	flags := log.LstdFlags | log.Lshortfile

	return &loggerImpl{
		infoLogger:  log.New(os.Stdout, "[INFO] ", flags),
		errorLogger: log.New(os.Stderr, "[ERROR] ", flags),
		warnLogger:  log.New(os.Stdout, "[WARN] ", flags),
		debugLogger: log.New(os.Stdout, "[DEBUG] ", flags),
	}
}

// Info logs an info message
func (l *loggerImpl) Info(msg string) {
	l.infoLogger.Println(msg)
}

// Error logs an error message
func (l *loggerImpl) Error(msg string, err error) {
	if err != nil {
		l.errorLogger.Printf("%s: %v", msg, err)
	} else {
		l.errorLogger.Println(msg)
	}
}

// Warn logs a warning message
func (l *loggerImpl) Warn(msg string) {
	l.warnLogger.Println(msg)
}

// Debug logs a debug message
func (l *loggerImpl) Debug(msg string) {
	l.debugLogger.Println(msg)
}
