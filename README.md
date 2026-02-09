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

- **Command-line interface**: Process CSV files with weather data
- **REST API**: HTTP endpoint for third-party developers to get fire risk predictions by coordinates

See [API_README.md](API_README.md) for detailed API documentation.


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

where `./bergen_2026_01_09.csv` is an example CSV demonstrating the input format which comes bundled with this repo.

# REST API

To run the REST API server:

```bash
python3 -m uvicorn frcm.api:app --host 0.0.0.0 --port 8000
```

See [API_README.md](API_README.md) for complete API documentation and usage examples.

# Overview

The implementation is organised into the following main folders:

- `datamodel` - contains an implementation of the data model used for weather data and fire risk indications.
- `fireriskmodel` contains an implementation of the underlying fire risk model.

The central method of the application is the method `compute()` in `fireriskmodel.compute`.

