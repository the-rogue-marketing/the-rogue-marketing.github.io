# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.13-slim AS builder

# Install uv from the official container image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Configure uv environment
ENV VIRTUAL_ENV=/opt/venv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Create virtual environment
RUN uv venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy dependency files first (layer caching optimization)
WORKDIR /build
COPY pyproject.toml uv.lock ./

# Install dependencies using frozen lockfile for reproducibility
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy the rest of the application code
COPY . .

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================
# Stage 2: Production Runtime
# ============================================
FROM python:3.13-slim

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set up the application directory
WORKDIR /app
COPY . /app

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Expose the FastAPI port
EXPOSE 8000

# Start the FastAPI server with uvicorn pointing to the lab assistant app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
