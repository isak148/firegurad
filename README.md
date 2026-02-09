# DYNAMIC Fire risk indicator implementation

This repository contains a _simplified version_ the implementation of the dynamic fire risk indicator
described in the submitted paper:

> R.D: Strand and L.M. Kristensen. [*An implementation, evaluation and validation of a dynamic fire and conflagration risk indicator for wooden homes*](https://doi.org/10.1016/j.procs.2024.05.195).

Compared to the [original version](https://github.com/webminz/dynamic-frcm), this repository
only contains the **fire risk calculation** itself (without the hard-wired integration with the https://met.no integration
and the more complex API).
The calculation takes a CSV dataset containing time, temperature, relative humidity, and wind speed data points and 
provides the resulting fire risk as _time to flashover (ttf)_.


# Installation

The project is based on using [uv](https://docs.astral.sh/uv/) as the package manager.
If you want to build this project on you own, make sure that [uv is installed correctly](https://docs.astral.sh/uv/getting-started/installation/).


afterwards you can build the package with:
```
uv build
```

Which will create the package _wheel_ (file ending `.whl`) in the `dist/` directory.
This package can ordinarily be installed with `pip install` and integrated into existing Python applications 
or it can be run standalone using `python -m`.

Alternatively you can test FRCM directly by running:

```shell
uv run python src/frcm/__main__.py ./bergen_2026_01_09.csv
```

where `./bergen_2026_01_09.csv` is an example CSV demostrating the input format which comes bundled with this repo.

# Overview

The implementation is organised into the following main folders:

- `datamodel` - contains an implementation of the data model used for weather data and fire risk indications.
- `fireriskmodel` contains an implementation of the underlying fire risk model.

The central method of the application is the method `compute()` in `fireriskmodel.compute`.

# REST API

This repository now includes a secure REST API for accessing the fire risk calculation functionality over HTTPS with authentication.

## Features

- **HTTPS Encryption**: All API communication is encrypted using TLS/SSL
- **API Key Authentication**: Protect endpoints with API key-based authentication
- **Self-signed Certificate Generation**: Automatic generation of SSL certificates for development
- **FastAPI Framework**: Modern, fast, and well-documented API framework
- **Interactive Documentation**: Swagger UI and ReDoc available at `/docs` and `/redoc`

## API Installation

Install the required dependencies:

```shell
uv sync
```

## Configuration

Create a `.env` file based on the provided `.env.example`:

```shell
cp .env.example .env
```

Edit the `.env` file to configure:

- `FRCM_API_KEYS`: Comma-separated list of valid API keys (e.g., `key1,key2,key3`)
- `FRCM_HOST`: Server host (default: `0.0.0.0`)
- `FRCM_PORT`: Server port (default: `8443`)
- `FRCM_SSL_CERT`: Path to SSL certificate (default: `./ssl/cert.pem`)
- `FRCM_SSL_KEY`: Path to SSL private key (default: `./ssl/key.pem`)
- `FRCM_REQUIRE_HTTPS`: Enable/disable HTTPS (default: `True`)

**Important**: For production use, always:
1. Set strong, random API keys
2. Use properly signed SSL certificates (not self-signed)
3. Keep HTTPS enabled (`FRCM_REQUIRE_HTTPS=True`)

## Starting the API Server

Start the API server with:

```shell
uv run frcm-api
```

Or directly:

```shell
uv run python -m frcm.api.server
```

The server will:
1. Check for SSL certificates (generate self-signed if missing)
2. Start on the configured port with HTTPS enabled
3. Require API key authentication for protected endpoints

## Using the API

### Health Check (No Authentication Required)

```bash
curl -k https://localhost:8443/health
```

### Calculate Fire Risk (Authentication Required)

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

### API Documentation

Access the interactive API documentation at:
- Swagger UI: `https://localhost:8443/docs`
- ReDoc: `https://localhost:8443/redoc`

**Note**: Use `-k` flag with curl to accept self-signed certificates in development.

## Security Notes

### Development vs Production

**Development**:
- Self-signed certificates are acceptable
- Can use simple API keys for testing
- HTTPS can be disabled for local testing (not recommended)

**Production**:
- Use certificates from a trusted Certificate Authority (Let's Encrypt, DigiCert, etc.)
- Use strong, randomly generated API keys
- Always enable HTTPS
- Consider implementing rate limiting
- Use environment variables or secret management systems for configuration
- Monitor API access logs
- Consider implementing OAuth2 for more advanced authentication needs

### Disabling HTTPS (Not Recommended)

For local development only, you can disable HTTPS:

```bash
export FRCM_REQUIRE_HTTPS=False
export FRCM_PORT=8080
uv run frcm-api
```

Then access via HTTP:
```bash
curl http://localhost:8080/health
```

**Warning**: Never disable HTTPS in production environments.


