# Docker Build Optimization Guide

## Quick Start (Fastest Build)

```bash
# Enable BuildKit (one-time setup)
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build with caching
docker-compose build

# Or use the optimized build script
chmod +x .docker-build.sh
./docker-build.sh
```

## Build Speed Optimizations Applied

### 1. **Multi-Stage Builds**
- Separates PyTorch installation (slow, rarely changes)
- Separates SAM 3 installation (slow, rarely changes)
- Separates application code (changes frequently)
- Each stage can be cached independently

### 2. **BuildKit Cache Mounts**
- Pip cache is mounted: `/root/.cache/pip`
- Subsequent builds reuse downloaded packages
- Dramatically speeds up pip installs

### 3. **Layer Ordering**
- Dependencies installed before code copy
- Code changes don't invalidate dependency cache
- Only rebuilds what actually changed

### 4. **Removed Unnecessary Operations**
- Removed `PIP_NO_CACHE_DIR=1` (conflicts with cache mounts)
- Combined RUN commands to reduce layers
- Removed verification step (can add back if needed)

## Build Time Comparison

**First Build (no cache):**
- Base image download: ~5-10 minutes (one-time)
- PyTorch installation: ~10-15 minutes
- SAM 3 installation: ~5-10 minutes
- Application setup: ~1 minute
- **Total: ~20-35 minutes** (one-time)

**Subsequent Builds (with cache):**
- Base image: Cached (0 seconds)
- PyTorch: Cached if unchanged (~0 seconds)
- SAM 3: Cached if unchanged (~0 seconds)
- Application: Only rebuilds if code changed (~30 seconds)
- **Total: ~30 seconds - 2 minutes** (code changes only)

## Tips for Faster Builds

### 1. Enable BuildKit (Required)
```bash
# Add to ~/.bashrc or ~/.zshrc
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

### 2. Use Build Cache
```bash
# Build with explicit cache
docker build --cache-from sam3-inference:latest -t sam3-inference:latest .
```

### 3. Pre-pull Base Image
```bash
# Pull base image separately (can resume if interrupted)
docker pull nvidia/cuda:12.6.3-devel-ubuntu22.04
```

### 4. Use Docker Buildx (Advanced)
```bash
# Create buildx builder with cache
docker buildx create --use --name cache-builder
docker buildx build --cache-from type=local,src=/tmp/.buildx-cache \
                     --cache-to type=local,dest=/tmp/.buildx-cache \
                     -t sam3-inference .
```

### 5. Build on Faster Connection
- Base image is 2.5GB - faster internet = faster first build
- Consider building on a machine with better bandwidth

## Troubleshooting

### Build Still Slow?
1. **Check BuildKit is enabled:**
   ```bash
   docker buildx version
   ```

2. **Verify cache is working:**
   ```bash
   docker build --progress=plain .  # Shows cache hits/misses
   ```

3. **Clear cache if corrupted:**
   ```bash
   docker builder prune
   ```

### Out of Disk Space?
```bash
# Clean up unused images
docker image prune -a

# Clean up build cache
docker builder prune -a
```

## Alternative: Use Pre-built Base Image

If you have access to a registry, you can pre-build and push the base stages:

```bash
# Build and push PyTorch stage
docker build --target pytorch-install -t your-registry/sam3-pytorch:latest .
docker push your-registry/sam3-pytorch:latest

# Build final image using pre-built base
docker build --target final --build-arg BASE_IMAGE=your-registry/sam3-pytorch:latest .
```
