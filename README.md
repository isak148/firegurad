# DYNAMIC Fire risk indicator implementation

This repository contains a _simplified version_ the implementation of the dynamic fire risk indicator
described in the submitted paper:

> R.D: Strand and L.M. Kristensen. [*An implementation, evaluation and validation of a dynamic fire and conflagration risk indicator for wooden homes*](https://doi.org/10.1016/j.procs.2024.05.195).

Compared to the [original version](https://github.com/webminz/dynamic-frcm), this repository
contains the **fire risk calculation** itself as well as a **weather data harvester** that automatically fetches
data from https://api.met.no for selected locations.

The calculation takes weather data (time, temperature, relative humidity, and wind speed) and 
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
- `fireriskmodel` - contains an implementation of the underlying fire risk model.
- `worker` - contains the weather data harvester for automatically fetching data from api.met.no.

The central method of the application is the method `compute()` in `fireriskmodel.compute`.

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


