"""Compute module with database caching support."""
from frcm.fireriskmodel.compute import compute as compute_raw
from frcm.database import get_database
import frcm.datamodel.model as dm


def compute_with_cache(wd: dm.WeatherData, use_cache: bool = True, 
                      db_path: str = "frcm_cache.db") -> dm.FireRiskPrediction:
    """Compute fire risk with database caching.
    
    This function checks if the fire risk prediction for the given weather data
    already exists in the database. If it does, it returns the cached result.
    Otherwise, it computes the fire risk, stores it in the database, and returns it.
    
    Args:
        wd: Weather data to compute fire risk for
        use_cache: Whether to use database caching (default: True)
        db_path: Path to the SQLite database file
        
    Returns:
        Fire risk prediction
    """
    if not use_cache:
        return compute_raw(wd)
    
    db = get_database(db_path)
    
    # Store weather data and get its hash
    data_hash = db.store_weather_data(wd)
    
    # Try to get cached prediction
    cached_prediction = db.get_fire_risk_prediction(data_hash)
    
    if cached_prediction is not None:
        print(f"Using cached fire risk prediction (hash: {data_hash[:16]}...)")
        return cached_prediction
    
    # Compute fire risk if not cached
    print(f"Computing new fire risk prediction (hash: {data_hash[:16]}...)")
    prediction = compute_raw(wd)
    
    # Store the prediction in the database
    db.store_fire_risk_prediction(data_hash, prediction)
    
    return prediction
