"""
Tests for the scheduled weather data harvester.
"""
import pytest
import time
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from frcm.worker.scheduled_harvester import ScheduledHarvester
from frcm.datamodel.model import WeatherData, WeatherDataPoint
from frcm.worker.locations import Location


@pytest.fixture
def temp_locations_file():
    """Create a temporary locations.json file for testing."""
    locations = {
        "locations": [
            {
                "name": "TestLocation",
                "latitude": 60.0,
                "longitude": 5.0,
                "altitude": 0
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(locations, f)
        temp_file = f.name
    
    yield temp_file
    
    # Cleanup
    Path(temp_file).unlink(missing_ok=True)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_weather_data():
    """Create mock weather data for testing."""
    now = datetime.now(timezone.utc)
    data_points = [
        WeatherDataPoint(
            timestamp=now,
            temperature=5.5,
            humidity=85.0,
            wind_speed=3.2
        )
    ]
    return WeatherData(data=data_points)


class TestScheduledHarvester:
    """Tests for the ScheduledHarvester class."""
    
    def test_init_with_valid_config(self, temp_locations_file, temp_output_dir):
        """Test initialization with valid configuration."""
        harvester = ScheduledHarvester(
            locations_file=temp_locations_file,
            output_dir=temp_output_dir,
            update_interval=60,
            forecast_hours=48
        )
        
        assert harvester.update_interval == 60
        assert harvester.forecast_hours == 48
        assert len(harvester.config.locations) == 1
        assert harvester.config.locations[0].name == "TestLocation"
    
    def test_init_with_nonexistent_locations_file(self, temp_output_dir):
        """Test initialization with non-existent locations file."""
        with pytest.raises(FileNotFoundError):
            ScheduledHarvester(
                locations_file="nonexistent.json",
                output_dir=temp_output_dir
            )
    
    def test_output_dir_creation(self, temp_locations_file):
        """Test that output directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "new_output"
            
            harvester = ScheduledHarvester(
                locations_file=temp_locations_file,
                output_dir=str(output_dir)
            )
            
            assert output_dir.exists()
            assert output_dir.is_dir()
    
    @patch('frcm.worker.scheduled_harvester.WeatherHarvester')
    @patch('frcm.worker.scheduled_harvester.compute')
    def test_fetch_and_process(
        self, 
        mock_compute,
        mock_harvester_class,
        temp_locations_file,
        temp_output_dir,
        mock_weather_data
    ):
        """Test fetch_and_process method."""
        # Setup mocks
        mock_harvester_instance = Mock()
        mock_harvester_class.return_value = mock_harvester_instance
        mock_harvester_instance.fetch_weather_data.return_value = mock_weather_data
        
        mock_fire_risk = Mock()
        mock_fire_risk.write_csv = Mock()
        mock_compute.return_value = mock_fire_risk
        
        # Create harvester
        harvester = ScheduledHarvester(
            locations_file=temp_locations_file,
            output_dir=temp_output_dir
        )
        
        # Run fetch_and_process
        harvester.fetch_and_process()
        
        # Verify weather data was fetched
        mock_harvester_instance.fetch_weather_data.assert_called_once()
        
        # Verify compute was called
        mock_compute.assert_called_once_with(mock_weather_data)
        
        # Verify CSV files were created
        weather_csv = Path(temp_output_dir) / "testlocation_weather.csv"
        assert weather_csv.exists()
    
    @patch('frcm.worker.scheduled_harvester.WeatherHarvester')
    def test_fetch_and_process_handles_api_error(
        self,
        mock_harvester_class,
        temp_locations_file,
        temp_output_dir
    ):
        """Test that fetch_and_process handles API errors gracefully."""
        from frcm.worker.harvester import MetNoAPIError
        
        # Setup mock to raise error
        mock_harvester_instance = Mock()
        mock_harvester_class.return_value = mock_harvester_instance
        mock_harvester_instance.fetch_weather_data.side_effect = MetNoAPIError("API Error")
        
        # Create harvester
        harvester = ScheduledHarvester(
            locations_file=temp_locations_file,
            output_dir=temp_output_dir
        )
        
        # This should not raise an exception
        harvester.fetch_and_process()
    
    def test_stop(self, temp_locations_file, temp_output_dir):
        """Test stopping the harvester."""
        harvester = ScheduledHarvester(
            locations_file=temp_locations_file,
            output_dir=temp_output_dir
        )
        
        harvester.running = True
        harvester.stop()
        
        assert harvester.running is False
    
    @patch('frcm.worker.scheduled_harvester.WeatherHarvester')
    @patch('frcm.worker.scheduled_harvester.compute')
    @patch('frcm.worker.scheduled_harvester.time.sleep')
    def test_run_single_cycle(
        self,
        mock_sleep,
        mock_compute,
        mock_harvester_class,
        temp_locations_file,
        temp_output_dir,
        mock_weather_data
    ):
        """Test running a single cycle of the harvester."""
        # Setup mocks
        mock_harvester_instance = Mock()
        mock_harvester_class.return_value = mock_harvester_instance
        mock_harvester_instance.fetch_weather_data.return_value = mock_weather_data
        
        mock_fire_risk = Mock()
        mock_fire_risk.write_csv = Mock()
        mock_compute.return_value = mock_fire_risk
        
        # Create harvester with short interval
        harvester = ScheduledHarvester(
            locations_file=temp_locations_file,
            output_dir=temp_output_dir,
            update_interval=1
        )
        
        # Stop after first sleep call
        def stop_on_sleep(*args):
            harvester.stop()
        
        mock_sleep.side_effect = stop_on_sleep
        
        # Run the harvester (will stop after one cycle)
        harvester.run()
        
        # Verify it ran at least once
        assert mock_harvester_instance.fetch_weather_data.call_count >= 1
    
    def test_custom_update_interval(self, temp_locations_file, temp_output_dir):
        """Test custom update interval."""
        harvester = ScheduledHarvester(
            locations_file=temp_locations_file,
            output_dir=temp_output_dir,
            update_interval=300  # 5 minutes
        )
        
        assert harvester.update_interval == 300
    
    def test_custom_forecast_hours(self, temp_locations_file, temp_output_dir):
        """Test custom forecast hours."""
        harvester = ScheduledHarvester(
            locations_file=temp_locations_file,
            output_dir=temp_output_dir,
            forecast_hours=72  # 3 days
        )
        
        assert harvester.forecast_hours == 72


def test_main_with_invalid_file():
    """Test main function with invalid locations file."""
    import sys
    from frcm.worker.scheduled_harvester import main
    
    # Mock sys.argv
    with patch.object(sys, 'argv', ['scheduled_harvester.py', 'nonexistent.json']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1


def test_main_with_keyboard_interrupt(temp_locations_file):
    """Test main function handles keyboard interrupt."""
    import sys
    from frcm.worker.scheduled_harvester import main
    
    with patch.object(sys, 'argv', ['scheduled_harvester.py', temp_locations_file]):
        with patch('frcm.worker.scheduled_harvester.ScheduledHarvester') as mock_class:
            mock_instance = Mock()
            mock_instance.run.side_effect = KeyboardInterrupt()
            mock_class.return_value = mock_instance
            
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
