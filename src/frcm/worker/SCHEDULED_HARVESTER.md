# Scheduled Weather Data Harvester

This module provides a scheduled worker that automatically fetches weather data from the MET (Meteorologisk institutt) Frost API at regular intervals.

## Features

- **Automatic Data Fetching**: Fetches temperature, humidity, and wind speed from MET API
- **Configurable Update Interval**: Default is every 60 seconds (1 minute)
- **Multiple Locations**: Monitor multiple locations simultaneously
- **Fire Risk Calculation**: Automatically computes fire risk predictions
- **CSV Output**: Saves weather data and fire risk predictions as CSV files
- **Graceful Shutdown**: Handles SIGINT and SIGTERM signals properly

## Quick Start

### 1. Create a Locations Configuration File

Create a `locations.json` file with the locations you want to monitor:

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

You can use the provided `locations_example.json` as a template.

### 2. Configure Environment Variables (Optional)

Create a `.env` file or set environment variables:

```bash
# Copy example configuration
cp .env.example .env

# Edit the configuration
nano .env
```

Configuration options:
- `FRCM_WORKER_UPDATE_INTERVAL`: Update interval in seconds (default: 60)
- `FRCM_WORKER_FORECAST_HOURS`: Hours to fetch in forecast (default: 48)
- `FRCM_WORKER_OUTPUT_DIR`: Output directory for CSV files (default: current directory)

### 3. Run the Scheduled Harvester

#### Using Python Module

```bash
# Run with default settings (updates every 60 seconds)
python -m frcm.worker.scheduled_harvester locations.json

# Custom update interval (every 5 minutes = 300 seconds)
python -m frcm.worker.scheduled_harvester locations.json --interval 300

# Custom output directory
python -m frcm.worker.scheduled_harvester locations.json --output ./weather_data

# Combine options
python -m frcm.worker.scheduled_harvester locations.json --interval 60 --output ./output --forecast-hours 72
```

#### Using uv

```bash
# Run with uv
uv run python -m frcm.worker.scheduled_harvester locations.json
```

## Command Line Arguments

```
usage: scheduled_harvester.py [-h] [--output OUTPUT] [--interval INTERVAL] 
                              [--forecast-hours FORECAST_HOURS] locations

positional arguments:
  locations             Path to locations.json configuration file

optional arguments:
  --output OUTPUT       Output directory for CSV files (default: current directory)
  --interval INTERVAL   Update interval in seconds (default: 60)
  --forecast-hours FORECAST_HOURS
                       Number of hours to fetch in forecast (default: 48)
```

## Output Files

For each location, the harvester generates two CSV files:

1. **Weather Data**: `{location_name}_weather.csv`
   - Contains temperature, humidity, and wind speed data
   - Format: `timestamp,temperature,humidity,wind_speed`

2. **Fire Risk Predictions**: `{location_name}_firerisk.csv`
   - Contains time-to-flashover (TTF) predictions
   - Format: `timestamp,ttf`

### Example Output Files

- `bergen_weather.csv` - Weather data for Bergen
- `bergen_firerisk.csv` - Fire risk predictions for Bergen
- `oslo_weather.csv` - Weather data for Oslo
- `oslo_firerisk.csv` - Fire risk predictions for Oslo

## Usage Examples

### Example 1: Monitor Every Minute (Default)

```bash
python -m frcm.worker.scheduled_harvester locations.json
```

This will:
- Fetch weather data from MET API every 60 seconds
- Save results to the current directory
- Monitor all locations in `locations.json`

### Example 2: Custom Interval and Output Directory

```bash
# Create output directory
mkdir -p /var/log/fireguard/weather

# Run with 5-minute interval
python -m frcm.worker.scheduled_harvester locations.json \
  --interval 300 \
  --output /var/log/fireguard/weather
```

### Example 3: Using Environment Variables

```bash
# Set environment variables
export FRCM_WORKER_UPDATE_INTERVAL=120  # 2 minutes
export FRCM_WORKER_OUTPUT_DIR=./output
export FRCM_WORKER_FORECAST_HOURS=72    # 3 days

# Run (will use environment variables)
python -m frcm.worker.scheduled_harvester locations.json
```

## Running as a Service

### systemd Service (Linux)

Create a systemd service file `/etc/systemd/system/fireguard-harvester.service`:

```ini
[Unit]
Description=FireGuard Weather Data Harvester
After=network.target

[Service]
Type=simple
User=fireguard
WorkingDirectory=/opt/fireguard
Environment="PATH=/opt/fireguard/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/fireguard/venv/bin/python -m frcm.worker.scheduled_harvester /opt/fireguard/locations.json --output /var/log/fireguard
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fireguard-harvester
sudo systemctl start fireguard-harvester
sudo systemctl status fireguard-harvester
```

View logs:

```bash
sudo journalctl -u fireguard-harvester -f
```

### Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install -e .

# Create output directory
RUN mkdir -p /app/output

# Run the scheduled harvester
CMD ["python", "-m", "frcm.worker.scheduled_harvester", "locations.json", "--output", "/app/output"]
```

Build and run:

```bash
docker build -t fireguard-harvester .
docker run -d --name fireguard-harvester \
  -v $(pwd)/locations.json:/app/locations.json \
  -v $(pwd)/output:/app/output \
  fireguard-harvester
```

## Programmatic Usage

You can also use the scheduled harvester programmatically in your Python code:

```python
from frcm.worker.scheduled_harvester import ScheduledHarvester

# Create and configure the harvester
harvester = ScheduledHarvester(
    locations_file="locations.json",
    output_dir="./output",
    update_interval=60,  # 1 minute
    forecast_hours=48     # 2 days
)

# Run continuously (blocking)
harvester.run()

# Or run a single fetch cycle
harvester.fetch_and_process()

# Stop the harvester
harvester.stop()
```

## Fetched Weather Parameters

The scheduled harvester fetches the following parameters from the MET API:

1. **Temperature** (`air_temperature`)
   - Unit: Celsius (°C)
   - Used for fire risk calculation

2. **Humidity** (`relative_humidity`)
   - Unit: Percent (%)
   - Used for fire risk calculation

3. **Wind Speed** (`wind_speed`)
   - Unit: Meters per second (m/s)
   - Used for fire risk calculation

All three parameters are required for accurate fire risk prediction.

## Logging

The harvester uses Python's logging module with INFO level by default. Logs include:

- Start/stop events
- Data fetch cycles
- API request results
- File save operations
- Errors and warnings

Example log output:

```
2026-02-10 12:00:00 - __main__ - INFO - Starting scheduled harvester (update interval: 60s)
2026-02-10 12:00:00 - __main__ - INFO - Monitoring 2 location(s)
2026-02-10 12:00:00 - __main__ - INFO - [2026-02-10 12:00:00] Starting data fetch cycle...
2026-02-10 12:00:01 - __main__ - INFO - Fetching weather data for Bergen
2026-02-10 12:00:02 - __main__ - INFO -   Temperature: 5.5°C, Humidity: 85.0%, Wind Speed: 3.2 m/s
2026-02-10 12:00:02 - __main__ - INFO - Fetched 48 weather data points
2026-02-10 12:00:02 - __main__ - INFO - Saved weather data to output/bergen_weather.csv
2026-02-10 12:00:03 - __main__ - INFO - Saved fire risk prediction to output/bergen_firerisk.csv
2026-02-10 12:00:03 - __main__ - INFO - Completed data fetch cycle at 2026-02-10 12:00:03
2026-02-10 12:00:03 - __main__ - INFO - Waiting 60 seconds until next update...
```

## Error Handling

The harvester includes comprehensive error handling:

- **Network Errors**: Retries on next cycle
- **API Errors**: Logs error and continues with next location
- **File I/O Errors**: Logs error and continues
- **Signal Handling**: Graceful shutdown on SIGINT/SIGTERM

## Performance Considerations

- **MET API Rate Limits**: The MET API has rate limits. Using 60-second intervals (default) is safe for most use cases.
- **Network Latency**: API requests typically take 1-3 seconds depending on network conditions.
- **Disk Space**: Each location generates approximately 1-2 MB per day with 1-minute intervals.

## Troubleshooting

### Issue: "Locations file not found"

**Solution**: Ensure the locations.json file exists and the path is correct.

```bash
# Check if file exists
ls -la locations.json

# Use absolute path
python -m frcm.worker.scheduled_harvester /full/path/to/locations.json
```

### Issue: "Failed to fetch weather data"

**Solution**: Check network connectivity and MET API status.

```bash
# Test API manually
curl "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=60.39&lon=5.32"
```

### Issue: "Permission denied" when writing files

**Solution**: Ensure the output directory exists and is writable.

```bash
# Create output directory with correct permissions
mkdir -p output
chmod 755 output

# Or specify a different directory
python -m frcm.worker.scheduled_harvester locations.json --output /tmp/weather
```

## Related Documentation

- [Worker Module README](README.md)
- [MET Integration Documentation](../met_integration/README.md)
- [Main Project README](../../../README.md)
- [API Quick Start](../../../API_QUICK_START.md)

## MET API Compliance

This harvester complies with MET API terms of service:
- Uses proper User-Agent header
- Respects rate limits
- Follows API documentation guidelines

See: https://api.met.no/doc/TermsOfService
