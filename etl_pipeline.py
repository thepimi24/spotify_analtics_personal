import sqlite3
from pathlib import Path

import os
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

from database import obtener_conexion, inicializar_db


load_dotenv(override=True)

SPOTIFY_SCOPE = "user-read-recently-played"


def conectar_spotify():
    """Crea la conexión autenticada con Spotify."""
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

    if not all([client_id, client_secret, redirect_uri]):
        raise ValueError("Faltan credenciales de Spotify en el archivo .env.")

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SPOTIFY_SCOPE,
    )

    return spotipy.Spotify(auth_manager=auth_manager)


def normalizar_timestamp(played_at):
    """Normaliza timestamps exportados por Spotify a un formato consistente."""
    if not played_at:
        return played_at

    if "." in played_at:
        return f"{played_at.split('.')[0]}Z"

    return played_at


def buscar_track_existente(cursor, track_name, artist_id):
    """Busca un track ya registrado por nombre normalizado y artista."""
    cursor.execute(
        """
        SELECT track_id
        FROM tracks
        WHERE LOWER(TRIM(track_name)) = LOWER(TRIM(?))
          AND artist_id = ?
        LIMIT 1
        """,
        (track_name, artist_id),
    )

    row = cursor.fetchone()
    return row[0] if row else None


def reproduccion_duplicada(cursor, track_id, played_at, ventana_segundos=90):
    """Evita registrar dos veces una reproducción casi idéntica."""
    cursor.execute(
        """
        SELECT 1
        FROM play_history
        WHERE track_id = ?
          AND ABS(
              (julianday(?) - julianday(played_at)) * 86400
          ) <= ?
        LIMIT 1
        """,
        (track_id, played_at, ventana_segundos),
    )

    return cursor.fetchone() is not None


def guardar_reproduccion(cursor, track, played_at):
    """Guarda artista, canción y reproducción en SQLite."""
    artista = track["artists"][0]

    artist_id = artista["id"]
    artist_name = artista["name"]

    cursor.execute(
        """
        INSERT OR IGNORE INTO artists (artist_id, artist_name)
        VALUES (?, ?)
        """,
        (artist_id, artist_name),
    )

    track_id = buscar_track_existente(
        cursor,
        track["name"],
        artist_id,
    ) or track["id"]

    cursor.execute(
        """
        INSERT OR IGNORE INTO tracks (
            track_id,
            track_name,
            artist_id,
            duration_ms
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            track_id,
            track["name"],
            artist_id,
            track["duration_ms"],
        ),
    )

    played_at = normalizar_timestamp(played_at)

    if reproduccion_duplicada(cursor, track_id, played_at):
        return False

    try:
        cursor.execute(
            """
            INSERT INTO play_history (track_id, played_at)
            VALUES (?, ?)
            """,
            (track_id, played_at),
        )
        return True
    except sqlite3.IntegrityError:
        return False


def ejecutar_etl():
    """Extrae reproducciones recientes y las incorpora a SQLite."""
    inicializar_db()

    spotify = conectar_spotify()
    conn = obtener_conexion()
    cursor = conn.cursor()

    print("🎧 Extrayendo historial reciente de Spotify...")

    try:
        resultado = spotify.current_user_recently_played(limit=50)
        nuevos_registros = 0

        for item in resultado.get("items", []):
            if guardar_reproduccion(
                cursor,
                item["track"],
                item["played_at"],
            ):
                nuevos_registros += 1

        conn.commit()
        print(f"✅ Se guardaron {nuevos_registros} reproducciones nuevas.")

    except Exception as error:
        conn.rollback()
        print(f"❌ Error durante el ETL: {error}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    ejecutar_etl()
