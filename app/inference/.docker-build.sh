#!/bin/bash
# Optimized Docker build script with BuildKit caching
# Usage: ./docker-build.sh [tag]

set -e

# Enable BuildKit for better caching
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

TAG=${1:-sam3-inference:latest}

echo "Building with BuildKit caching enabled..."
echo "Tag: $TAG"
echo ""

# Build with cache mount for faster pip installs
docker build \
  --tag "$TAG" \
  --cache-from "$TAG" \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --progress=plain \
  .

echo ""
echo "Build complete! Image tagged as: $TAG"
echo ""
echo "To run:"
echo "  docker run --gpus all -p 8000:8000 -e HF_TOKEN=your_token $TAG"
