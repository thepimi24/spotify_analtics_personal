import os
import sqlite3
import time

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "spotify_data.db",
)


# ============================================================
# CARGAR CREDENCIALES
# ============================================================

load_dotenv()

CLIENT_ID = os.getenv(
    "SPOTIPY_CLIENT_ID"
)

CLIENT_SECRET = os.getenv(
    "SPOTIPY_CLIENT_SECRET"
)

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError(
        "Faltan SPOTIPY_CLIENT_ID "
        "o SPOTIPY_CLIENT_SECRET en .env"
    )


# ============================================================
# CONEXIÓN CON SPOTIFY
# ============================================================

auth_manager = SpotifyClientCredentials(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)

spotify = spotipy.Spotify(
    auth_manager=auth_manager
)


# ============================================================
# BASE DE DATOS
# ============================================================

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()


# ============================================================
# OBTENER TRACKS SIN ÁLBUM
# ============================================================

cursor.execute(
    """
    SELECT
        track_id,
        track_name
    FROM tracks
    WHERE
        album_id IS NULL
        OR album_name IS NULL
    """
)

tracks = cursor.fetchall()

print(
    f"Tracks pendientes: {len(tracks)}"
)


# ============================================================
# PROCESAMIENTO
# ============================================================

actualizados = 0
errores = 0


for i, (track_id, track_name) in enumerate(
    tracks,
    start=1,
):

    try:

        print(
            f"[{i}/{len(tracks)}] "
            f"{track_name}"
        )

        track = spotify.track(
            track_id
        )

        album = track.get(
            "album",
            {}
        )

        album_id = album.get(
            "id"
        )

        album_name = album.get(
            "name"
        )

        album_type = album.get(
            "album_type"
        )

        album_release_date = album.get(
            "release_date"
        )

        cursor.execute(
            """
            UPDATE tracks
            SET
                album_id = ?,
                album_name = ?,
                album_type = ?,
                album_release_date = ?
            WHERE
                track_id = ?
            """,
            (
                album_id,
                album_name,
                album_type,
                album_release_date,
                track_id,
            ),
        )

        actualizados += 1

        # Guardar cada cierto número
        if actualizados % 50 == 0:

            conn.commit()

            print(
                "💾 Progreso guardado."
            )

        # Pequeña pausa
        time.sleep(0.05)

    except Exception as e:

        errores += 1

        print(
            f"❌ Error con "
            f"{track_name}: {e}"
        )


# ============================================================
# GUARDAR
# ============================================================

conn.commit()

conn.close()


# ============================================================
# RESUMEN
# ============================================================

print()
print("=" * 60)
print("PROCESO FINALIZADO")
print("=" * 60)

print(
    f"Tracks actualizados: {actualizados}"
)

print(
    f"Errores: {errores}"
)