# DYNAMIC Fire risk indicator implementation

This repository contains a _simplified version_ the implementation of the dynamic fire risk indicator
described in the submitted paper:

> R.D: Strand and L.M. Kristensen. [*An implementation, evaluation and validation of a dynamic fire and conflagration risk indicator for wooden homes*](https://doi.org/10.1016/j.procs.2024.05.195).

Compared to the [original version](https://github.com/webminz/dynamic-frcm), this repository
only contains the **fire risk calculation** itself (without the hard-wired integration with the https://met.no integration
and the more complex API).
The calculation takes a CSV dataset containing time, temperature, relative humidity, and wind speed data points and 
provides the resulting fire risk as _time to flashover (ttf)_.

## Features

- **Database Caching**: Automatically caches weather data and computed fire risk results to minimize redundant computations
- **Efficient Storage**: Uses SQLite database to store both input weather data and calculated fire hazard results
- **Hash-based Lookup**: Identifies duplicate weather data sets using SHA-256 hashing for instant cache retrieval


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
- `fireriskmodel` contains an implementation of the underlying fire risk model.
- `database` - contains the database implementation for caching weather data and fire risk predictions.

The central method of the application is the method `compute()` in `fireriskmodel.compute`.
For cached computation, use `compute_with_cache()` from `fireriskmodel.compute_cached`.


