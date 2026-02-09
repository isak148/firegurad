"""Tests for database caching functionality."""
import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone

from frcm.database import Database
from frcm.datamodel.model import WeatherData, WeatherDataPoint, FireRisk, FireRiskPrediction


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    
    db = Database(db_path)
    yield db
    
    db.close()
    os.unlink(db_path)


@pytest.fixture
def sample_weather_data():
    """Create sample weather data for testing."""
    data_points = [
        WeatherDataPoint(
            timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            temperature=10.0,
            humidity=80.0,
            wind_speed=5.0
        ),
        WeatherDataPoint(
            timestamp=datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
            temperature=11.0,
            humidity=75.0,
            wind_speed=4.5
        ),
        WeatherDataPoint(
            timestamp=datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc),
            temperature=12.0,
            humidity=70.0,
            wind_speed=4.0
        ),
    ]
    return WeatherData(data=data_points)


@pytest.fixture
def sample_fire_risk():
    """Create sample fire risk prediction for testing."""
    risks = [
        FireRisk(timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc), ttf=5.0),
        FireRisk(timestamp=datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc), ttf=5.5),
        FireRisk(timestamp=datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc), ttf=6.0),
    ]
    return FireRiskPrediction(firerisks=risks)


def test_database_initialization(temp_db):
    """Test that database tables are created correctly."""
    cursor = temp_db.conn.cursor()
    
    # Check weather_data table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='weather_data'
    """)
    assert cursor.fetchone() is not None
    
    # Check fire_risk_predictions table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='fire_risk_predictions'
    """)
    assert cursor.fetchone() is not None


def test_store_and_retrieve_weather_data(temp_db, sample_weather_data):
    """Test storing and retrieving weather data."""
    # Store weather data
    data_hash = temp_db.store_weather_data(sample_weather_data)
    
    assert data_hash is not None
    assert len(data_hash) == 64  # SHA-256 produces 64 hex characters
    
    # Retrieve weather data
    retrieved_data = temp_db.get_weather_data(data_hash)
    
    assert retrieved_data is not None
    assert len(retrieved_data.data) == len(sample_weather_data.data)
    assert retrieved_data.data[0].temperature == sample_weather_data.data[0].temperature
    assert retrieved_data.data[0].humidity == sample_weather_data.data[0].humidity


def test_store_duplicate_weather_data(temp_db, sample_weather_data):
    """Test that storing duplicate weather data doesn't cause errors."""
    # Store the same data twice
    hash1 = temp_db.store_weather_data(sample_weather_data)
    hash2 = temp_db.store_weather_data(sample_weather_data)
    
    # Should get the same hash
    assert hash1 == hash2
    
    # Should only have one entry in database
    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM weather_data")
    count = cursor.fetchone()[0]
    assert count == 1


def test_store_and_retrieve_fire_risk_prediction(temp_db, sample_weather_data, sample_fire_risk):
    """Test storing and retrieving fire risk predictions."""
    # Store weather data first
    data_hash = temp_db.store_weather_data(sample_weather_data)
    
    # Store fire risk prediction
    temp_db.store_fire_risk_prediction(data_hash, sample_fire_risk)
    
    # Retrieve fire risk prediction
    retrieved_prediction = temp_db.get_fire_risk_prediction(data_hash)
    
    assert retrieved_prediction is not None
    assert len(retrieved_prediction.firerisks) == len(sample_fire_risk.firerisks)
    assert retrieved_prediction.firerisks[0].ttf == sample_fire_risk.firerisks[0].ttf


def test_retrieve_nonexistent_weather_data(temp_db):
    """Test retrieving non-existent weather data returns None."""
    result = temp_db.get_weather_data("nonexistent_hash_1234567890")
    assert result is None


def test_retrieve_nonexistent_fire_risk(temp_db):
    """Test retrieving non-existent fire risk prediction returns None."""
    result = temp_db.get_fire_risk_prediction("nonexistent_hash_1234567890")
    assert result is None


def test_hash_consistency(temp_db, sample_weather_data):
    """Test that the same weather data produces the same hash."""
    hash1 = temp_db._compute_hash(sample_weather_data)
    hash2 = temp_db._compute_hash(sample_weather_data)
    
    assert hash1 == hash2


def test_different_data_different_hash(temp_db, sample_weather_data):
    """Test that different weather data produces different hashes."""
    hash1 = temp_db._compute_hash(sample_weather_data)
    
    # Modify the data
    modified_data = WeatherData(data=[
        WeatherDataPoint(
            timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            temperature=15.0,  # Different temperature
            humidity=80.0,
            wind_speed=5.0
        )
    ])
    
    hash2 = temp_db._compute_hash(modified_data)
    
    assert hash1 != hash2
