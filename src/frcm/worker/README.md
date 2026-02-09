# Weather Data Harvester Worker

This module provides functionality for automatically harvesting weather data from the Norwegian Meteorological Institute (MET Norway) API at https://api.met.no

## Features

- Fetch weather forecast data for multiple locations
- Convert MET Norway API data to FRCM WeatherData format
- Automatically compute fire risk predictions
- Save results as CSV files

## Usage

### Basic Usage

Create a JSON file with your locations (see `locations_example.json`):

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

Run the worker:

```bash
python -m frcm.worker locations.json [output_dir]
```

### Programmatic Usage

```python
from frcm.worker.harvester import WeatherHarvester
from frcm.worker.locations import Location
from frcm.fireriskmodel.compute import compute

# Create a location
location = Location(
    name="Bergen",
    latitude=60.3913,
    longitude=5.3221,
    altitude=12
)

# Fetch weather data
harvester = WeatherHarvester()
weather_data = harvester.fetch_weather_data(location, hours=48)

# Compute fire risk
fire_risk = compute(weather_data)

# Save results
weather_data.write_csv("bergen_weather.csv")
fire_risk.write_csv("bergen_firerisk.csv")
```

## API Requirements

The MET Norway API requires:
- A proper User-Agent header identifying your application
- Adherence to their [Terms of Service](https://api.met.no/doc/TermsOfService)
- Caching of responses to minimize load on their servers

The harvester automatically includes the User-Agent header: `firegurad/0.1.0 github.com/isak148/firegurad`

## Output Files

The worker generates two CSV files per location:

1. `{location_name}_weather.csv` - Raw weather data
   - Columns: timestamp, temperature, humidity, wind_speed
   
2. `{location_name}_firerisk.csv` - Fire risk predictions
   - Columns: timestamp, ttf (time to flashover)

## Error Handling

The worker handles common errors:
- Network connectivity issues
- API rate limiting
- Invalid location coordinates
- Missing or malformed data

Errors are logged but don't stop processing of other locations.
