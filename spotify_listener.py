import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "spotify_data.db"

# Cada cuánto consultar Spotify.
# 30 segundos es un buen equilibrio para este proyecto.
INTERVALO_SEGUNDOS = 30

# Spotify permite consultar hasta 50 reproducciones recientes.
LIMITE_HISTORIAL = 50

SCOPE = "user-read-recently-played"


# ============================================================
# CARGA DE CONFIGURACIÓN
# ============================================================

load_dotenv(
    BASE_DIR / ".env",
    override=True,
)


# ============================================================
# CONEXIÓN A SQLITE
# ============================================================

def obtener_conexion():
    """Abre una conexión a la base de datos."""

    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
    )

    conn.execute(
        "PRAGMA foreign_keys = ON;"
    )

    return conn


# ============================================================
# INFRAESTRUCTURA
# ============================================================

def asegurar_infraestructura(conn):
    """
    Verifica que las tablas e índices necesarios
    existan antes de iniciar el listener.
    """

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS artists (
            artist_id TEXT PRIMARY KEY,
            artist_name TEXT NOT NULL,
            popularity INTEGER,
            genres TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tracks (
            track_id TEXT PRIMARY KEY,
            track_name TEXT NOT NULL,
            artist_id TEXT,
            duration_ms INTEGER,
            tempo REAL,
            energy REAL,
            valence REAL,
            FOREIGN KEY (
                artist_id
            )
            REFERENCES artists(artist_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS play_history (
            play_id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT,
            played_at TEXT UNIQUE,
            FOREIGN KEY (
                track_id
            )
            REFERENCES tracks(track_id)
        )
        """
    )

    # Registro de cada sincronización.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ingestion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checked_at TEXT NOT NULL,
            new_streams INTEGER DEFAULT 0,
            status TEXT NOT NULL,
            error_message TEXT
        )
        """
    )

    # Índices para acelerar las consultas.
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_play_history_track_id
        ON play_history(track_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_play_history_played_at
        ON play_history(played_at)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_tracks_artist_id
        ON tracks(artist_id)
        """
    )

    conn.commit()


# ============================================================
# SPOTIFY
# ============================================================

def conectar_spotify():
    """
    Crea la conexión autenticada con Spotify.
    """

    client_id = os.getenv(
        "SPOTIPY_CLIENT_ID"
    )

    client_secret = os.getenv(
        "SPOTIPY_CLIENT_SECRET"
    )

    redirect_uri = os.getenv(
        "SPOTIPY_REDIRECT_URI"
    )

    if not client_id:
        raise ValueError(
            "No se encontró SPOTIPY_CLIENT_ID."
        )

    if not client_secret:
        raise ValueError(
            "No se encontró SPOTIPY_CLIENT_SECRET."
        )

    if not redirect_uri:
        raise ValueError(
            "No se encontró SPOTIPY_REDIRECT_URI."
        )

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        cache_path=str(
            BASE_DIR / ".spotify_cache"
        ),
    )

    return spotipy.Spotify(
        auth_manager=auth_manager
    )


# ============================================================
# UTILIDADES
# ============================================================

def ahora_utc():
    """
    Devuelve la fecha/hora actual en UTC.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


def normalizar_timestamp(timestamp):
    """
    Normaliza el timestamp entregado por Spotify.

    Spotify normalmente devuelve timestamps ISO 8601.
    """

    if not timestamp:
        return None

    return timestamp.strip()


# ============================================================
# REGISTRO DE SINCRONIZACIONES
# ============================================================

def registrar_sincronizacion(
    conn,
    nuevas,
    estado,
    error=None,
):
    """
    Guarda información sobre cada ciclo
    de sincronización.
    """

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO ingestion_log (
            checked_at,
            new_streams,
            status,
            error_message
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            ahora_utc(),
            nuevas,
            estado,
            error,
        ),
    )

    conn.commit()


# ============================================================
# ARTISTAS
# ============================================================

def guardar_artista(
    cursor,
    artist_id,
    artist_name,
):
    """
    Inserta el artista si todavía no existe.
    """

    if not artist_id:
        return

    cursor.execute(
        """
        INSERT OR IGNORE INTO artists (
            artist_id,
            artist_name
        )
        VALUES (?, ?)
        """,
        (
            artist_id,
            artist_name,
        ),
    )


# ============================================================
# TRACKS
# ============================================================

def guardar_track(
    cursor,
    track,
    artist_id,
):
    """
    Inserta o actualiza la información básica
    de una canción.
    """

    track_id = track.get("id")

    track_name = track.get(
        "name",
        "Unknown",
    )

    duration_ms = track.get(
        "duration_ms"
    )

    if not track_id:
        return None

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
            track_name,
            artist_id,
            duration_ms,
        ),
    )

    return track_id


# ============================================================
# DUPLICADOS
# ============================================================

def reproduccion_ya_existe(
    cursor,
    played_at,
):
    """
    Comprueba si una reproducción ya fue guardada.

    El timestamp de reproducción funciona como
    identificador único para el historial.
    """

    cursor.execute(
        """
        SELECT 1
        FROM play_history
        WHERE played_at = ?
        LIMIT 1
        """,
        (played_at,),
    )

    return cursor.fetchone() is not None


# ============================================================
# PROCESAMIENTO DE HISTORIAL
# ============================================================

def procesar_historial(
    conn,
    resultados,
):
    """
    Procesa todas las reproducciones recibidas
    desde Spotify.

    Devuelve la cantidad de streams nuevos.
    """

    cursor = conn.cursor()

    nuevas = 0

    items = resultados.get(
        "items",
        [],
    )

    for item in items:

        track = item.get(
            "track"
        )

        played_at = normalizar_timestamp(
            item.get("played_at")
        )

        if not track or not played_at:
            continue

        track_id = track.get(
            "id"
        )

        artistas = track.get(
            "artists",
            []
        )

        if not track_id or not artistas:
            continue

        artist = artistas[0]

        artist_id = artist.get(
            "id"
        )

        artist_name = artist.get(
            "name",
            "Unknown",
        )

        if not artist_id:
            continue

        # ----------------------------------------------------
        # ARTISTA
        # ----------------------------------------------------

        guardar_artista(
            cursor,
            artist_id,
            artist_name,
        )

        # ----------------------------------------------------
        # TRACK
        # ----------------------------------------------------

        guardar_track(
            cursor,
            track,
            artist_id,
        )

        # ----------------------------------------------------
        # DUPLICADOS
        # ----------------------------------------------------

        if reproduccion_ya_existe(
            cursor,
            played_at,
        ):
            continue

        # ----------------------------------------------------
        # NUEVA REPRODUCCIÓN
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO play_history (
                track_id,
                played_at
            )
            VALUES (?, ?)
            """,
            (
                track_id,
                played_at,
            ),
        )

        nuevas += 1

        print(
            f"🎵 Nueva reproducción: "
            f"{track.get('name')} — "
            f"{artist_name}"
        )

    conn.commit()

    return nuevas


# ============================================================
# SINCRONIZACIÓN
# ============================================================

def sincronizar(sp, conn):
    """
    Ejecuta una sincronización completa
    contra el historial reciente de Spotify.
    """

    try:

        resultados = (
            sp.current_user_recently_played(
                limit=LIMITE_HISTORIAL
            )
        )

        nuevas = procesar_historial(
            conn,
            resultados,
        )

        registrar_sincronizacion(
            conn,
            nuevas,
            "success",
        )

        return nuevas

    except Exception as error:

        mensaje = str(error)

        registrar_sincronizacion(
            conn,
            0,
            "error",
            mensaje,
        )

        print(
            f"⚠️ Error durante la sincronización: "
            f"{mensaje}"
        )

        return 0


# ============================================================
# ESTADO DEL LISTENER
# ============================================================

def mostrar_estado(
    nuevas,
    ultima_sincronizacion,
):
    """
    Muestra información sencilla del estado
    del listener.
    """

    hora = datetime.now().strftime(
        "%H:%M:%S"
    )

    print(
        "\n"
        "----------------------------------------"
    )

    print(
        f"🟢 Listener activo"
    )

    print(
        f"🕐 Hora: {hora}"
    )

    print(
        f"📥 Streams nuevos: {nuevas}"
    )

    print(
        f"⏱️ Próxima consulta en "
        f"{INTERVALO_SEGUNDOS} segundos"
    )

    print(
        "----------------------------------------\n"
    )


# ============================================================
# LISTENER PRINCIPAL
# ============================================================

def iniciar_listener():

    print(
        "\n🎧 SPOTIFY LISTENER"
    )

    print(
        "========================================"
    )

    print(
        f"📁 Base de datos: {DB_PATH}"
    )

    print(
        f"⏱️ Intervalo: "
        f"{INTERVALO_SEGUNDOS} segundos"
    )

    print(
        "========================================\n"
    )

    conn = obtener_conexion()

    try:

        asegurar_infraestructura(
            conn
        )

        sp = conectar_spotify()

        print(
            "✅ Conexión con Spotify establecida."
        )

        print(
            "🚀 Comenzando monitoreo...\n"
        )

        while True:

            inicio = time.time()

            nuevas = sincronizar(
                sp,
                conn,
            )

            mostrar_estado(
                nuevas,
                inicio,
            )

            time.sleep(
                INTERVALO_SEGUNDOS
            )

    except KeyboardInterrupt:

        print(
            "\n🛑 Listener detenido manualmente."
        )

    except Exception as error:

        print(
            f"\n❌ Error crítico: {error}"
        )

    finally:

        conn.close()

        print(
            "🔒 Conexión a SQLite cerrada."
        )


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    iniciar_listener()