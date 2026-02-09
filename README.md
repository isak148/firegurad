# FireGuard

**FireGuard** is a dynamic fire risk assessment system that provides real-time fire risk calculations for wooden homes based on weather conditions.

## Vision

FireGuard aims to provide an accessible, API-driven platform for calculating dynamic fire risk indicators. By integrating meteorological data and advanced fire risk modeling, we empower developers, researchers, and safety organizations to build applications that enhance fire safety awareness and prevention.

## Quick Links

- ** Documentation**: [Technical implementation details](#overview) (see below)
- ** Source Code**: [GitHub Repository](https://github.com/isak148/firegurad)
- ** Backlog**: [GitHub Issues & Project Board](https://github.com/isak148/firegurad/issues)

---

## About the Implementation

This repository contains a _simplified version_ of the implementation of the dynamic fire risk indicator
[![CI](https://github.com/isak148/firegurad/workflows/CI/badge.svg)](https://github.com/isak148/firegurad/actions/workflows/ci.yml)

This repository contains a _simplified version_ the implementation of the dynamic fire risk indicator
described in the submitted paper:

> R.D: Strand and L.M. Kristensen. [*An implementation, evaluation and validation of a dynamic fire and conflagration risk indicator for wooden homes*](https://doi.org/10.1016/j.procs.2024.05.195).

Compared to the [original version](https://github.com/webminz/dynamic-frcm), this repository
contains the **fire risk calculation** itself as well as a **weather data harvester** that automatically fetches
data from https://api.met.no for selected locations.

The calculation takes weather data (time, temperature, relative humidity, and wind speed) and 
provides the resulting fire risk as _time to flashover (ttf)_.

## New: MET API Integration

This repository now includes integration with the Meteorologisk institutt (MET) API, enabling automatic weather data fetching instead of relying solely on CSV files. See [MET Integration Documentation](src/frcm/met_integration/README.md) for details.
## Features

- **Database Caching**: Automatically caches weather data and computed fire risk results to minimize redundant computations
- **Efficient Storage**: Uses SQLite database to store both input weather data and calculated fire hazard results
- **Hash-based Lookup**: Identifies duplicate weather data sets using SHA-256 hashing for instant cache retrieval


- **Dynamic Fire Risk Calculation**: Compute time to flashover (ttf) based on weather conditions
- **Weather Data Processing**: Parse and process CSV datasets with temperature, humidity, and wind data
- **Python Package**: Easily integrate into existing Python applications
- **Command-line Interface**: Run calculations standalone for quick testing
- **Research-backed Model**: Based on peer-reviewed academic research

## Installation

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

## Overview
## Database Caching

The application automatically caches weather data and fire risk predictions in a SQLite database (`frcm_cache.db`).
When the same weather data is processed again, the cached results are retrieved instantly instead of recalculating.

The caching system:
- Stores weather data with a unique hash based on the data content
- Caches fire risk predictions linked to their corresponding weather data
- Automatically checks for cached results before performing calculations
- Uses minimal disk space with efficient SQLite storage

On first run with a dataset:
```
Computing new fire risk prediction (hash: 4c2a1af09503b8aa...)
```

On subsequent runs with the same dataset:
```
Using cached fire risk prediction (hash: 4c2a1af09503b8aa...)
```

# Overview

The implementation is organised into the following main folders:

- `datamodel` - contains an implementation of the data model used for weather data and fire risk indications.
- `worker` - contains the weather data harvester for automatically fetching data from api.met.no.
- `fireriskmodel` contains an implementation of the underlying fire risk model.
- `notification` - contains the notification service for publishing fire danger changes.
- `database` - contains the database implementation for caching weather data and fire risk predictions.

The central method of the application is the method `compute()` in `fireriskmodel.compute`.
For cached computation, use `compute_with_cache()` from `fireriskmodel.compute_cached`.


# System Architecture

For information about the complete FireGuard system architecture, including integration with MET API, database, message queues, and REST API endpoints, please see the [Architecture Documentation](docs/architecture.md).

The architecture documentation includes:
- System component overview
- Data flow diagrams
- Deployment architecture
- Technology stack recommendations
- API specifications

## Contributing

Contributions are welcome! Please check our [issue tracker](https://github.com/isak148/firegurad/issues) to see ongoing work and planned features.

Current development focus includes:
- REST API implementation
- MET (Meteorological Institute) API integration
- Database persistence
- Security and authentication
- Notification services

## License

This project is licensed under the terms found in the [COPYING.txt](COPYING.txt) file.

## Maintainers

- Lars Michael Kristensen
- Patrick Stünkel

---

**FireGuard** - Enhancing fire safety through intelligent risk assessment.
## Usage Examples

### Using CSV file (original method)

```shell
uv run python src/frcm/__main__.py ./bergen_2026_01_09.csv
```

### Using MET API (new method)

```python
from frcm import fetch_and_transform_weather_data, compute

# Fetch weather data for a location
weather_data = fetch_and_transform_weather_data(latitude=60.39, longitude=5.32)

# Compute fire risk
fire_risks = compute(weather_data)
print(fire_risks)
```

See `examples/met_api_example.py` for a complete example.

# Notification Service

The FRCM now includes a notification service that publishes alerts when the fire danger level changes. The service uses MQTT protocol to notify subscribers about fire risk changes in real-time.

## Fire Danger Levels

The notification service categorizes fire risk into four levels based on Time to Flashover (TTF):

- **LOW**: TTF > 60 minutes - Safe conditions
- **MODERATE**: 30 < TTF ≤ 60 minutes - Exercise caution
- **HIGH**: 15 < TTF ≤ 30 minutes - Be vigilant
- **VERY_HIGH**: TTF ≤ 15 minutes - Take immediate precautions

## Configuration

To enable notifications, configure the service using environment variables. Copy the `.env.example` file to `.env` and adjust the settings:

```bash
# Enable notifications
FRCM_NOTIFICATIONS_ENABLED=true

# MQTT Broker settings
FRCM_MQTT_BROKER_HOST=localhost
FRCM_MQTT_BROKER_PORT=1883
FRCM_MQTT_TOPIC=frcm/fire-danger

# Optional authentication
FRCM_MQTT_USERNAME=your_username
FRCM_MQTT_PASSWORD=your_password
```

## Message Format

When the fire danger level changes, the service publishes a JSON message to the configured MQTT topic:

```json
{
  "timestamp": "2026-01-09T12:00:00",
  "danger_level": "HIGH",
  "ttf_minutes": 25.5,
  "message": "Fire danger is HIGH - be vigilant"
}
```

## Usage Example

Run FRCM with notifications enabled:

```bash
export FRCM_NOTIFICATIONS_ENABLED=true
export FRCM_MQTT_BROKER_HOST=mqtt.example.com
uv run python src/frcm/__main__.py ./bergen_2026_01_09.csv
```

## MQTT Broker Setup

For testing, you can use a public MQTT broker or run one locally:

```bash
# Using Docker
docker run -d -p 1883:1883 eclipse-mosquitto

# Or install locally
sudo apt-get install mosquitto mosquitto-clients
```

Subscribe to notifications:

```bash
mosquitto_sub -h localhost -t frcm/fire-danger
```


# Usage

## Manual Calculation from CSV

You can calculate fire risk from a CSV file containing weather data:

```shell
python -m frcm ./bergen_2026_01_09.csv [output.csv]
```

The CSV file should have the format:
```
timestamp,temperature,humidity,wind_speed
2026-01-07T00:00:00+00:00,-9.7,85.0,0.8
```

## Automatic Weather Data Harvesting

The worker module automatically fetches weather data from the Norwegian Meteorological Institute (api.met.no)
for configured locations and computes fire risk predictions:

1. Create a locations configuration file (`locations.json`):
```json
{
  "locations": [
    {
      "name": "Bergen",
      "latitude": 60.3913,
      "longitude": 5.3221,
      "altitude": 12
    },
    {
      "name": "Oslo",
      "latitude": 59.9139,
      "longitude": 10.7522,
      "altitude": 23
    }
  ]
}
```

2. Run the worker:
```shell
python -m frcm.worker locations.json [output_dir]
```

This will:
- Fetch weather forecasts for each location from api.met.no
- Compute fire risk predictions
- Save results as CSV files: `{location}_weather.csv` and `{location}_firerisk.csv`

See `src/frcm/worker/README.md` for more details and programmatic usage examples.


