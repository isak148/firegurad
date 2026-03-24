"""Database implementation for caching weather data, predictions, and historical records."""
import sqlite3
import json
import hashlib
import secrets
import hmac
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone, timedelta
import frcm.datamodel.model as dm


class Database:
    """Database for caching weather data and fire risk predictions."""

    PASSWORD_HASH_ITERATIONS = 200_000
    
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

        # Table for user accounts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Table for simple bearer sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Table for user favorite locations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_favorite_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                location_key TEXT NOT NULL,
                name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, location_key),
                FOREIGN KEY (user_id) REFERENCES users(id)
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

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email
            ON users(email)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_sessions_token
            ON user_sessions(token)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_favorites_user_id
            ON user_favorite_locations(user_id)
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

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Hash password using PBKDF2-HMAC-SHA256."""
        password_bytes = password.encode("utf-8")
        salt_bytes = salt.encode("utf-8")
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password_bytes,
            salt_bytes,
            Database.PASSWORD_HASH_ITERATIONS,
        )
        return digest.hex()

    def create_user(self, name: str, email: str, password: str) -> dict:
        """Create a new user account."""
        created_at = datetime.now(timezone.utc).isoformat()
        normalized_email = email.strip().lower()
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, password_salt, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name.strip(), normalized_email, password_hash, salt, created_at),
            )
            self.conn.commit()
        except sqlite3.IntegrityError as e:
            if "users.email" in str(e):
                raise ValueError("A user with this email already exists")
            raise

        user_id = cursor.lastrowid
        return {
            "id": user_id,
            "name": name.strip(),
            "email": normalized_email,
            "created_at": created_at,
        }

    def verify_user_credentials(self, email: str, password: str) -> Optional[dict]:
        """Verify login credentials and return user on success."""
        normalized_email = email.strip().lower()
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, name, email, password_hash, password_salt, created_at
            FROM users
            WHERE email = ?
            """,
            (normalized_email,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        user_id, name, user_email, stored_hash, salt, created_at = row
        computed_hash = self._hash_password(password, salt)
        if not hmac.compare_digest(stored_hash, computed_hash):
            return None

        return {
            "id": user_id,
            "name": name,
            "email": user_email,
            "created_at": created_at,
        }

    def create_user_session(self, user_id: int, expires_hours: int = 24) -> str:
        """Create bearer session token for a user."""
        token = secrets.token_urlsafe(32)
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=expires_hours)

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_sessions (user_id, token, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, token, expires_at.isoformat(), created_at.isoformat()),
        )
        self.conn.commit()
        return token

    def get_user_by_session_token(self, token: str) -> Optional[dict]:
        """Return user info for valid (non-expired) session token."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT u.id, u.name, u.email, u.created_at
            FROM user_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ? AND s.expires_at > ?
            LIMIT 1
            """,
            (token, now),
        )
        row = cursor.fetchone()
        if not row:
            return None

        user_id, name, email, created_at = row
        return {
            "id": user_id,
            "name": name,
            "email": email,
            "created_at": created_at,
        }

    def upsert_user_favorite_location(
        self,
        user_id: int,
        location_key: str,
        name: str,
        latitude: float,
        longitude: float,
    ) -> dict:
        """Create or update a user's favorite location."""
        created_at = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_favorite_locations (
                user_id, location_key, name, latitude, longitude, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, location_key)
            DO UPDATE SET
                name = excluded.name,
                latitude = excluded.latitude,
                longitude = excluded.longitude
            """,
            (user_id, location_key, name.strip(), latitude, longitude, created_at),
        )
        self.conn.commit()

        return {
            "location_key": location_key,
            "name": name.strip(),
            "latitude": latitude,
            "longitude": longitude,
        }

    def get_user_favorite_locations(self, user_id: int) -> list[dict]:
        """Return all favorite locations for a user."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT location_key, name, latitude, longitude
            FROM user_favorite_locations
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "location_key": row[0],
                "name": row[1],
                "latitude": row[2],
                "longitude": row[3],
            }
            for row in rows
        ]

    def delete_user_favorite_location(self, user_id: int, location_key: str) -> bool:
        """Delete a favorite location for a user by location key."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            DELETE FROM user_favorite_locations
            WHERE user_id = ? AND location_key = ?
            """,
            (user_id, location_key),
        )
        self.conn.commit()
        return cursor.rowcount > 0


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
