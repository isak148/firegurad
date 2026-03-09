"""Database implementation for caching weather data, predictions, and historical records."""
import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
import frcm.datamodel.model as dm


class Database:
    """Database for caching weather data and fire risk predictions."""
    
    def __init__(self, db_path: str = "frcm_cache.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Create database tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Table for weather data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hash TEXT UNIQUE NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Table for fire risk predictions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fire_risk_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                weather_data_hash TEXT NOT NULL,
                prediction_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (weather_data_hash) REFERENCES weather_data(data_hash)
            )
        """)
        
        # Table for append-only historical weather snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historical_weather_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_name TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                data_json TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )
        """)

        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_weather_hash 
            ON weather_data(data_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prediction_hash 
            ON fire_risk_predictions(weather_data_hash)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_historical_location_time
            ON historical_weather_data(location_name, fetched_at)
        """)
        
        self.conn.commit()
    
    def _compute_hash(self, weather_data: dm.WeatherData) -> str:
        """Compute a hash of weather data for caching.
        
        Args:
            weather_data: Weather data to hash
            
        Returns:
            Hash string
        """
        # Convert to JSON and compute hash
        data_str = weather_data.to_json()
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def store_weather_data(self, weather_data: dm.WeatherData) -> str:
        """Store weather data in the database.
        
        Args:
            weather_data: Weather data to store
            
        Returns:
            Hash of the stored data
        """
        data_hash = self._compute_hash(weather_data)
        data_json = weather_data.to_json()
        
        # Get time range from data
        if len(weather_data.data) > 0:
            start_time = weather_data.data[0].timestamp.isoformat()
            end_time = weather_data.data[-1].timestamp.isoformat()
        else:
            start_time = end_time = datetime.now(timezone.utc).isoformat()
        
        created_at = datetime.now(timezone.utc).isoformat()
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO weather_data (data_hash, start_time, end_time, data_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (data_hash, start_time, end_time, data_json, created_at))
            self.conn.commit()
        except sqlite3.IntegrityError:
            # Data already exists, that's fine
            pass
        
        return data_hash
    
    def get_weather_data(self, data_hash: str) -> Optional[dm.WeatherData]:
        """Retrieve weather data from the database.
        
        Args:
            data_hash: Hash of the weather data to retrieve
            
        Returns:
            WeatherData object if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT data_json FROM weather_data WHERE data_hash = ?
        """, (data_hash,))
        
        row = cursor.fetchone()
        if row:
            data_json = row[0]
            return dm.WeatherData.model_validate_json(data_json)
        return None
    
    def store_fire_risk_prediction(self, weather_data_hash: str, 
                                   prediction: dm.FireRiskPrediction) -> None:
        """Store fire risk prediction in the database.
        
        Args:
            weather_data_hash: Hash of the weather data used for prediction
            prediction: Fire risk prediction to store
        """
        prediction_json = prediction.model_dump_json()
        created_at = datetime.now(timezone.utc).isoformat()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO fire_risk_predictions (weather_data_hash, prediction_json, created_at)
            VALUES (?, ?, ?)
        """, (weather_data_hash, prediction_json, created_at))
        self.conn.commit()
    
    def get_fire_risk_prediction(self, weather_data_hash: str) -> Optional[dm.FireRiskPrediction]:
        """Retrieve fire risk prediction from the database.
        
        Args:
            weather_data_hash: Hash of the weather data
            
        Returns:
            FireRiskPrediction object if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT prediction_json FROM fire_risk_predictions 
            WHERE weather_data_hash = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (weather_data_hash,))
        
        row = cursor.fetchone()
        if row:
            prediction_json = row[0]
            return dm.FireRiskPrediction.model_validate_json(prediction_json)
        return None

    def store_historical_weather_data(self, weather_data: dm.WeatherData,
                                      location_name: Optional[str] = None) -> None:
        """Store weather data as an append-only historical snapshot.

        Args:
            weather_data: Weather data snapshot to store
            location_name: Optional location name associated with the snapshot
        """
        data_json = weather_data.to_json()

        if len(weather_data.data) > 0:
            start_time = weather_data.data[0].timestamp.isoformat()
            end_time = weather_data.data[-1].timestamp.isoformat()
        else:
            now = datetime.now(timezone.utc).isoformat()
            start_time = now
            end_time = now

        fetched_at = datetime.now(timezone.utc).isoformat()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO historical_weather_data (location_name, start_time, end_time, data_json, fetched_at)
            VALUES (?, ?, ?, ?, ?)
        """, (location_name, start_time, end_time, data_json, fetched_at))
        self.conn.commit()

    def get_historical_weather_data(self, location_name: Optional[str] = None,
                                    limit: Optional[int] = None) -> list[dm.WeatherData]:
        """Retrieve historical weather snapshots.

        Args:
            location_name: Optional location to filter by
            limit: Optional max number of snapshots (most recent first)

        Returns:
            List of WeatherData snapshots in descending fetch time order
        """
        cursor = self.conn.cursor()

        query = "SELECT data_json FROM historical_weather_data"
        params = []

        if location_name is not None:
            query += " WHERE location_name = ?"
            params.append(location_name)

        query += " ORDER BY fetched_at DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        return [dm.WeatherData.model_validate_json(row[0]) for row in rows]
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


# Global database instance
_database: Optional[Database] = None


def get_database(db_path: str = "frcm_cache.db") -> Database:
    """Get or create global database instance.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        Database instance
    """
    global _database
    if _database is None or _database.db_path != db_path:
        if _database is not None:
            _database.close()
        _database = Database(db_path)
    return _database
