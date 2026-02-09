# Docker Setup Guide

This guide explains how to run the FireGuard application using Docker and Docker Compose.

## Prerequisites

- Docker (version 20.10 or later)
- Docker Compose (version 2.0 or later)

## Quick Start

1. **Create environment configuration:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and set your API keys:
   ```env
   FRCM_API_KEYS=your-secret-api-key-1,your-secret-api-key-2
   ```

2. **Start the application:**
   ```bash
   docker compose up -d
   ```

3. **Access the API:**
   The API will be available at `https://localhost:8443`

   Test the health endpoint:
   ```bash
   curl -k https://localhost:8443/health
   ```

## Configuration

### Environment Variables

The application uses environment variables from the `.env` file. Key variables:

- `FRCM_API_KEYS`: Comma-separated list of valid API keys
- `FRCM_HOST`: Server host (default: `0.0.0.0`)
- `FRCM_PORT`: Server port (default: `8443`)
- `FRCM_SSL_CERT`: Path to SSL certificate
- `FRCM_SSL_KEY`: Path to SSL private key
- `FRCM_REQUIRE_HTTPS`: Enable/disable HTTPS (default: `True`)

### SSL Certificates

The application will automatically generate self-signed SSL certificates on first run if they don't exist. For production, provide your own certificates:

1. Place your certificate files in the `./ssl` directory
2. Update the `.env` file to point to your certificates

### Data Persistence

The following directories are mounted for persistence:

- `./ssl`: SSL certificates
- `./data`: Cache database (`frcm_cache.db`)

## Usage

### Start Services

```bash
# Start only the API
docker compose up -d

# Start with MQTT broker (for notifications)
docker compose --profile with-mqtt up -d
```

### View Logs

```bash
# View all logs
docker compose logs -f

# View only API logs
docker compose logs -f frcm-api

# View only MQTT logs
docker compose logs -f mqtt-broker
```

### Stop Services

```bash
docker compose down
```

### Rebuild After Changes

```bash
docker compose up -d --build
```

## API Endpoints

Once running, the following endpoints are available:

- `GET /health` - Health check (no authentication)
- `GET /api-info` - API information
- `POST /calculate` - Calculate fire risk (requires API key)
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

Example API call:

```bash
curl -k -X POST https://localhost:8443/calculate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-1" \
  -d '{
    "data": [
      {
        "timestamp": "2026-01-09T00:00:00",
        "temperature": 5.5,
        "humidity": 0.85,
        "wind_speed": 3.2
      }
    ]
  }'
```

## MQTT Broker (Optional)

To enable notifications with an MQTT broker:

1. Start services with the MQTT profile:
   ```bash
   docker compose --profile with-mqtt up -d
   ```

2. Configure MQTT in `.env`:
   ```env
   FRCM_NOTIFICATIONS_ENABLED=true
   FRCM_MQTT_BROKER_HOST=mqtt-broker
   FRCM_MQTT_BROKER_PORT=1883
   FRCM_MQTT_TOPIC=frcm/fire-danger
   ```

3. Subscribe to notifications:
   ```bash
   docker compose exec mqtt-broker mosquitto_sub -t frcm/fire-danger
   ```

## Troubleshooting

### Port Already in Use

Change the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8444:8443"  # Change 8444 to your preferred port
```

### Permission Issues

If you encounter permission issues with mounted volumes:
```bash
sudo chown -R $(id -u):$(id -g) ssl/ data/
```

### View Container Status

```bash
docker compose ps
```

### Access Container Shell

```bash
docker compose exec frcm-api /bin/bash
```

### Check Container Logs for Errors

```bash
docker compose logs frcm-api --tail=100
```

## Development

### Local Development with Docker

For local development, you can mount the source code:

```yaml
services:
  frcm-api:
    volumes:
      - ./src:/app/src  # Mount source code for live reloading
```

### Running Tests in Docker

```bash
docker compose exec frcm-api uv run pytest tests/
```

## Production Deployment

For production deployment:

1. Use proper SSL certificates from a trusted CA (e.g., Let's Encrypt)
2. Set strong, randomly generated API keys
3. Enable HTTPS (`FRCM_REQUIRE_HTTPS=True`)
4. Use Docker secrets or a secrets manager for sensitive data
5. Configure proper logging and monitoring
6. Set up automatic container restarts
7. Consider using a reverse proxy (nginx, Traefik) for additional security

## Architecture

The Docker setup includes:

- **frcm-api**: Main application container running the FastAPI server
- **mqtt-broker** (optional): Eclipse Mosquitto MQTT broker for notifications
- **frcm-network**: Bridge network for inter-service communication

## Support

For issues or questions, please refer to:
- [Main README](README.md)
- [API Documentation](API_README.md)
- [GitHub Issues](https://github.com/isak148/firegurad/issues)
