# Use Python 3.11 base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables
ENV UV_SYSTEM_PYTHON=1
ENV PYTHONUNBUFFERED=1

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY .env.example ./

# Install dependencies using uv with system Python
RUN uv sync --frozen --no-dev

# Create directories for SSL certificates and cache
RUN mkdir -p /app/ssl /app/data

# Expose the API port
EXPOSE 8443

# Run the API server using uv run
CMD ["uv", "run", "--no-dev", "frcm-api"]
