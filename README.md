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
- `notification` - contains the notification service for publishing fire danger changes.

The central method of the application is the method `compute()` in `fireriskmodel.compute`.

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


