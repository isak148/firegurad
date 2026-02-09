# FRCM API Quick Start Guide

## Overview
This guide shows how to use the FRCM Fire Risk Calculation API with HTTPS and authentication.

## Installation

```bash
# Install dependencies
pip install -e .

# Or with uv
uv sync
```

## Configuration

Create a `.env` file:

```bash
# Copy the example configuration
cp .env.example .env

# Edit the .env file to set your API keys
nano .env
```

Example `.env` configuration:

```env
FRCM_API_KEYS=your-secret-key-1,your-secret-key-2
FRCM_HOST=0.0.0.0
FRCM_PORT=8443
FRCM_SSL_CERT=./ssl/cert.pem
FRCM_SSL_KEY=./ssl/key.pem
FRCM_REQUIRE_HTTPS=True
```

## Starting the Server

```bash
# Start the API server
frcm-api

# Or directly
python -m frcm.api.server
```

The server will:
1. Automatically generate self-signed SSL certificates if needed
2. Start on port 8443 with HTTPS enabled
3. Require API key authentication for protected endpoints

## Using the API

### Health Check (No Authentication)

```bash
curl -k https://localhost:8443/health
```

Response:
```json
{"status": "healthy"}
```

### API Information

```bash
curl -k https://localhost:8443/api-info
```

### Calculate Fire Risk (Authentication Required)

```bash
curl -k -X POST https://localhost:8443/calculate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key-1" \
  -d '{
    "data": [
      {
        "timestamp": "2026-01-09T00:00:00",
        "temperature": 5.5,
        "humidity": 0.85,
        "wind_speed": 3.2
      },
      {
        "timestamp": "2026-01-09T01:00:00",
        "temperature": 5.2,
        "humidity": 0.87,
        "wind_speed": 3.0
      }
    ]
  }'
```

Response:
```json
{
  "firerisks": [
    {
      "timestamp": "2026-01-09T00:00:00",
      "ttf": 6.072481167177002
    },
    {
      "timestamp": "2026-01-09T01:00:00",
      "ttf": 5.730216250201331
    }
  ]
}
```

## Security Notes

### Development vs Production

**Development:**
- Use the `-k` flag with curl to accept self-signed certificates
- Can use simple API keys for testing
- HTTPS can be disabled by setting `FRCM_REQUIRE_HTTPS=False`

**Production:**
- Use certificates from a trusted Certificate Authority
- Generate strong, random API keys
- Always enable HTTPS
- Store API keys securely (environment variables, secret manager)
- Monitor API access logs
- Consider rate limiting

### Generating Strong API Keys

```bash
# Generate a random API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Disabling Authentication (Not Recommended)

To disable authentication for testing:
```env
FRCM_API_KEYS=
```

**Warning:** Never disable authentication in production!

### Using Production Certificates

Replace self-signed certificates with CA-signed ones:

1. Obtain certificates from Let's Encrypt or another CA
2. Update `.env` to point to your certificate files:
   ```env
   FRCM_SSL_CERT=/path/to/your/cert.pem
   FRCM_SSL_KEY=/path/to/your/key.pem
   ```

## Testing

Run the test suite:

```bash
pytest tests/test_api.py -v
```

## Troubleshooting

### Port Already in Use

Change the port in `.env`:
```env
FRCM_PORT=8444
```

### Certificate Generation Failed

Ensure OpenSSL is installed:
```bash
# Ubuntu/Debian
sudo apt-get install openssl

# macOS
brew install openssl
```

### Cannot Connect to Server

1. Check if server is running: `ps aux | grep frcm`
2. Check logs for errors
3. Verify firewall settings allow the configured port
4. Try disabling HTTPS temporarily for debugging

## API Endpoints

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/` | GET | No | API information |
| `/health` | GET | No | Health check |
| `/api-info` | GET | No | API usage information |
| `/calculate` | POST | Yes | Calculate fire risk |
| `/docs` | GET | No | Swagger UI (if enabled) |
| `/redoc` | GET | No | ReDoc documentation (if enabled) |

## Example: Python Client

```python
import requests
import json

# Disable SSL verification for self-signed certificates
# Remove verify=False for production with proper certificates
API_URL = "https://localhost:8443"
API_KEY = "your-secret-key-1"

# Health check
response = requests.get(f"{API_URL}/health", verify=False)
print(response.json())

# Calculate fire risk
weather_data = {
    "data": [
        {
            "timestamp": "2026-01-09T00:00:00",
            "temperature": 5.5,
            "humidity": 0.85,
            "wind_speed": 3.2
        }
    ]
}

response = requests.post(
    f"{API_URL}/calculate",
    headers={"X-API-Key": API_KEY},
    json=weather_data,
    verify=False
)

print(json.dumps(response.json(), indent=2))
```

## Additional Resources

- FastAPI Documentation: https://fastapi.tiangolo.com/
- Let's Encrypt: https://letsencrypt.org/
- OWASP API Security: https://owasp.org/www-project-api-security/
