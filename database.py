import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "spotify_data.db"


def obtener_conexion():
    """Abre una conexión a la base de datos de Spotify."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def inicializar_db():
    """Crea las tablas e índices necesarios para el proyecto."""
    conn = obtener_conexion()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS artists (
            artist_id TEXT PRIMARY KEY,
            artist_name TEXT NOT NULL,
            popularity INTEGER,
            genres TEXT
        );

        CREATE TABLE IF NOT EXISTS tracks (
            track_id TEXT PRIMARY KEY,
            track_name TEXT NOT NULL,
            artist_id TEXT,
            duration_ms INTEGER,
            tempo REAL,
            energy REAL,
            valence REAL,
            FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
        );

        CREATE TABLE IF NOT EXISTS play_history (
            play_id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT,
            played_at TEXT UNIQUE,
            FOREIGN KEY (track_id) REFERENCES tracks(track_id)
        );

        CREATE INDEX IF NOT EXISTS idx_play_history_track_id
            ON play_history(track_id);

        CREATE INDEX IF NOT EXISTS idx_play_history_played_at
            ON play_history(played_at);

        CREATE INDEX IF NOT EXISTS idx_tracks_artist_id
            ON tracks(artist_id);
        """
    )

    conn.commit()
    conn.close()
    print("✅ Base de datos e infraestructura listas.")


if __name__ == "__main__":
    inicializar_db()
