# Video Annotation Platform Backend - Phase 1

This is the backend API for the Video Annotation Platform, built with Go, Fiber, PostgreSQL, and GORM.

## Phase 1 Features

- Health check endpoint
- Video metadata CRUD operations
- S3 storage abstraction (interface only)
- Basic JWT middleware structure
- Swagger API documentation
- Docker containerization

## Prerequisites

- Go 1.25.2 or higher
- PostgreSQL 16 or higher
- Docker and Docker Compose (for containerized setup)
- AWS S3 credentials (optional, for storage)

## Local Development Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd framesense-monorepo/app/backend
```

### 2. Install dependencies

```bash
go mod download
```

### 3. Set up environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
SERVER_PORT=8080
ENVIRONMENT=development

DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=framesense
DB_SSLMODE=disable

JWT_SECRET=your-secret-key-change-in-production

S3_REGION=us-east-1
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_ENDPOINT=  # Optional: for S3-compatible services
```

### 4. Set up PostgreSQL database

Make sure PostgreSQL is running and create the database:

```bash
createdb framesense
```

Or using psql:

```sql
CREATE DATABASE framesense;
```

### 5. Run the application

```bash
go run cmd/server/main.go
```

The API will be available at `http://localhost:8080`

## Docker Setup

### Using Docker Compose

From the repository root:

```bash
docker-compose up --build
```

This will start:
- PostgreSQL database on port 5432
- API server on port 8080

### Environment Variables for Docker

Set environment variables in `.env` file at the repository root or export them:

```bash
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_NAME=framesense
export JWT_SECRET=your-secret-key
```

## API Endpoints

### Health Check

```
GET /health
```

Returns:
```json
{
  "success": true,
  "data": "ok"
}
```

### Video Endpoints

#### Create Video Metadata

```
POST /videos
Content-Type: application/json

{
  "title": "Sample Video",
  "description": "Video description",
  "s3_key": "videos/sample-video.mp4"
}
```

#### Get All Videos

```
GET /videos
```

#### Get Video by ID

```
GET /videos/:id
```

## Swagger Documentation

Once the server is running, access Swagger UI at:

```
http://localhost:8080/swagger/index.html
```

## Project Structure

```
backend/
├── cmd/
│   └── server/          # Application entry point
├── api/
│   ├── controllers/     # HTTP handlers
│   └── routes/          # Route definitions
├── internal/
│   └── video/           # Video domain (service + repository)
├── pkg/
│   ├── app/             # Application container
│   ├── database/        # Database connection
│   ├── logger/          # Logging utilities
│   ├── middleware/      # JWT middleware
│   └── storage/         # S3 storage abstraction
├── types/               # DTOs (Request/Response types)
├── config/              # Configuration management
├── migrations/          # Database migrations
└── docs/                # Swagger documentation
```

## Generating Swagger Documentation

To regenerate Swagger docs after making changes:

```bash
swag init -g cmd/server/main.go -o docs
```

Make sure `swag` is installed:

```bash
go install github.com/swaggo/swag/cmd/swag@latest
```

## Development Notes

- Database migrations are handled automatically via GORM AutoMigrate
- JWT middleware is implemented but not enforced on routes in Phase 1
- S3 storage interface is ready but actual upload logic will be added in Phase 2
- All DTOs are defined in the `types/` package

## Next Steps (Phase 2+)

- User authentication endpoints
- JWT token generation
- Actual file upload handling
- Inference service integration
- WebSocket support
- Background job processing

## License

Apache 2.0
