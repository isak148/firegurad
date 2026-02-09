"""
Basic tests for the FRCM fire risk calculation module.
"""
import pytest
from pathlib import Path
from frcm.datamodel.model import WeatherData, WeatherDataPoint
from frcm.fireriskmodel.compute import compute


def test_import_modules():
    """Test that core modules can be imported."""
    from frcm import console_main
    from frcm.datamodel.model import WeatherData, FireRisk
    from frcm.fireriskmodel.compute import compute
    assert console_main is not None
    assert WeatherData is not None
    assert FireRisk is not None
    assert compute is not None


def test_weather_data_point_creation():
    """Test creating a WeatherDataPoint."""
    from datetime import datetime
    point = WeatherDataPoint(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        temperature=20.0,
        humidity=60.0,
        wind_speed=5.0
    )
    assert point.temperature == 20.0
    assert point.humidity == 60.0
    assert point.wind_speed == 5.0


def test_weather_data_from_csv():
    """Test reading weather data from the example CSV file."""
    test_file = Path(__file__).parent.parent / "bergen_2026_01_09.csv"
    if test_file.exists():
        wd = WeatherData.read_csv(test_file)
        assert len(wd.data) > 0
        assert isinstance(wd.data[0], WeatherDataPoint)


def test_compute_fire_risk():
    """Test computing fire risk with sample data."""
    from datetime import datetime
    test_file = Path(__file__).parent.parent / "bergen_2026_01_09.csv"
    if test_file.exists():
        wd = WeatherData.read_csv(test_file)
        result = compute(wd)
        assert result is not None
        assert hasattr(result, 'firerisks')
        assert len(result.firerisks) > 0
