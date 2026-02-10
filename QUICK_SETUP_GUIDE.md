# Quick Setup Guide: MET API Weather Data Fetching

This guide shows you how to quickly set up automatic weather data fetching from the MET (Meteorologisk institutt) Frost API.

## What You Get

The scheduled harvester automatically fetches:
- **Temperature** (°C)
- **Humidity** (%)
- **Wind Speed** (m/s)

And computes fire risk predictions based on this data.

## 1-Minute Setup

### Step 1: Create Locations File

Create `my_locations.json`:

```json
{
  "locations": [
    {
      "name": "Bergen",
      "latitude": 60.3913,
      "longitude": 5.3221,
      "altitude": 12
    }
  ]
}
```

Or use the provided example:
```bash
cp locations_example.json my_locations.json
```

### Step 2: Run the Harvester

**Update every minute (default):**
```bash
python -m frcm.worker.scheduled_harvester my_locations.json
```

**Update every 5 minutes:**
```bash
python -m frcm.worker.scheduled_harvester my_locations.json --interval 300
```

**Save to custom directory:**
```bash
python -m frcm.worker.scheduled_harvester my_locations.json --output ./weather_data
```

### Step 3: Check the Output

The harvester creates CSV files for each location:
- `{location}_weather.csv` - Raw weather data (temperature, humidity, wind speed)
- `{location}_firerisk.csv` - Fire risk predictions (time to flashover)

Example:
```
output/
  ├── bergen_weather.csv
  └── bergen_firerisk.csv
```

## Configuration Options

### Command Line

```bash
python -m frcm.worker.scheduled_harvester <locations.json> \
  --interval 60 \              # Update interval in seconds
  --output ./output \          # Output directory
  --forecast-hours 48          # Hours of forecast data
```

### Environment Variables

Create a `.env` file:

```bash
FRCM_WORKER_UPDATE_INTERVAL=60      # 1 minute
FRCM_WORKER_FORECAST_HOURS=48       # 2 days
FRCM_WORKER_OUTPUT_DIR=./output
```

Then simply run:
```bash
python -m frcm.worker.scheduled_harvester my_locations.json
```

## Common Use Cases

### Case 1: Real-time Monitoring (1-minute updates)
```bash
python -m frcm.worker.scheduled_harvester locations.json
```

### Case 2: Periodic Checks (5-minute updates)
```bash
python -m frcm.worker.scheduled_harvester locations.json --interval 300
```

### Case 3: Hourly Updates
```bash
python -m frcm.worker.scheduled_harvester locations.json --interval 3600
```

### Case 4: Multiple Locations
Edit `locations.json` to include multiple locations:
```json
{
  "locations": [
    {"name": "Bergen", "latitude": 60.39, "longitude": 5.32, "altitude": 12},
    {"name": "Oslo", "latitude": 59.91, "longitude": 10.75, "altitude": 23},
    {"name": "Trondheim", "latitude": 63.43, "longitude": 10.40, "altitude": 5}
  ]
}
```

## Running as a Background Service

### Linux (systemd)

1. Create `/etc/systemd/system/fireguard.service`:
```ini
[Unit]
Description=FireGuard Weather Harvester
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/firegurad
ExecStart=/usr/bin/python3 -m frcm.worker.scheduled_harvester locations.json
Restart=always

[Install]
WantedBy=multi-user.target
```

2. Enable and start:
```bash
sudo systemctl enable fireguard
sudo systemctl start fireguard
sudo systemctl status fireguard
```

### Docker

```bash
docker run -d \
  -v $(pwd)/locations.json:/app/locations.json \
  -v $(pwd)/output:/app/output \
  fireguard-harvester \
  python -m frcm.worker.scheduled_harvester /app/locations.json --output /app/output
```

## Stopping the Harvester

Press `Ctrl+C` to stop gracefully, or send SIGTERM:
```bash
kill <pid>
```

## Logs

The harvester logs:
- Start/stop events
- Each data fetch cycle
- Weather parameters fetched
- Errors (with automatic retry)

Example log output:
```
INFO - Starting scheduled harvester (update interval: 60s)
INFO - Fetching weather data for Bergen
INFO -   Temperature: 5.5°C, Humidity: 85.0%, Wind Speed: 3.2 m/s
INFO - Fetched 48 weather data points
INFO - Saved weather data to bergen_weather.csv
INFO - Waiting 60 seconds until next update...
```

## Troubleshooting

**Problem**: "Locations file not found"
```bash
# Solution: Check file path
ls -la my_locations.json
```

**Problem**: "Failed to fetch weather data"
```bash
# Solution: Check network connectivity
curl https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=60.39&lon=5.32
```

**Problem**: "Permission denied" writing files
```bash
# Solution: Create output directory with write permissions
mkdir -p output
chmod 755 output
```

## Next Steps

- Read the [Full Documentation](src/frcm/worker/SCHEDULED_HARVESTER.md)
- Check the [Example Script](examples/scheduled_harvester_example.py)
- Learn about [MET API Integration](src/frcm/met_integration/README.md)

## Summary

You now have automatic weather data fetching! The harvester:
✅ Fetches temperature, humidity, and wind speed from MET API
✅ Updates every minute (or your custom interval)
✅ Computes fire risk predictions
✅ Saves data to CSV files
✅ Handles errors gracefully
✅ Runs continuously until stopped
