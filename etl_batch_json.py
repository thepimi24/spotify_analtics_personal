import json
import os
import sqlite3
import time
from pathlib import Path

import pandas as pd

from database import obtener_conexion, inicializar_db
from extractor import conectar_spotify


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def cargar_jsons(ruta_carpeta):
    """Lee todos los JSON de Spotify dentro de una carpeta."""
    archivos = sorted(ruta_carpeta.glob("*.json"))
    registros = []

    print(f"📁 Se encontraron {len(archivos)} archivos JSON.")

    for archivo in archivos:
        with archivo.open("r", encoding="utf-8") as file:
            registros.extend(json.load(file))

    return pd.DataFrame(registros)


def obtener_columnas_spotify(df):
    """Detecta los nombres de columnas usados por las distintas exportaciones."""
    columnas = {
        "artist": [
            "master_metadata_album_artist_name",
            "artistName",
        ],
        "track": [
            "master_metadata_track_name",
            "trackName",
        ],
        "uri": [
            "spotify_track_uri",
        ],
        "duration": [
            "ms_played",
            "msPlayed",
        ],
        "timestamp": [
            "ts",
            "endTime",
        ],
    }

    resultado = {}

    for nombre, opciones in columnas.items():
        resultado[nombre] = next(
            (col for col in opciones if col in df.columns),
            None,
        )

    return resultado


def limpiar_historial(df):
    """Limpia registros incompletos y elimina reproducciones menores a 30 segundos."""
    columnas = obtener_columnas_spotify(df)

    requeridas = ["artist", "track", "duration", "timestamp"]

    if any(columnas[col] is None for col in requeridas):
        raise ValueError(
            "El JSON no tiene el formato esperado de Spotify. "
            "Revisa las columnas disponibles."
        )

    artist_col = columnas["artist"]
    track_col = columnas["track"]
    duration_col = columnas["duration"]

    df = df.dropna(
        subset=[artist_col, track_col, duration_col]
    ).copy()

    df = df[df[duration_col] >= 30_000].copy()

    return df, columnas


def crear_track_id(row, columnas):
    """Genera un ID estable cuando el export no trae spotify_track_uri."""
    artist = str(row[columnas["artist"]]).strip().lower().replace(" ", "_")
    track = str(row[columnas["track"]]).strip().lower().replace(" ", "_")

    return f"local_{artist}__{track}"


def preparar_track_ids(df, columnas):
    """Usa el ID de Spotify cuando existe y crea uno local como respaldo."""
    uri_col = columnas["uri"]

    if uri_col is None:
        df["track_id"] = df.apply(
            lambda row: crear_track_id(row, columnas),
            axis=1,
        )
        return df

    tiene_uri = (
        df[uri_col].notna()
        & df[uri_col].astype(str).str.startswith("spotify:track:")
    )

    df["track_id"] = None

    df.loc[tiene_uri, "track_id"] = (
        df.loc[tiene_uri, uri_col]
        .astype(str)
        .str.replace("spotify:track:", "", regex=False)
    )

    faltantes = df["track_id"].isna()

    if faltantes.any():
        df.loc[faltantes, "track_id"] = df.loc[
            faltantes
        ].apply(
            lambda row: crear_track_id(row, columnas),
            axis=1,
        )

    return df


def resolver_artist_id(spotify, cache, artist_name):
    """Busca el ID real de Spotify y reutiliza resultados previamente consultados."""
    clave = artist_name.strip().lower()

    if clave in cache:
        return cache[clave]

    artist_id = None

    try:
        resultado = spotify.search(
            q=f'artist:"{artist_name}"',
            type="artist",
            limit=1,
        )

        items = resultado.get("artists", {}).get("items", [])

        if items:
            artist_id = items[0]["id"]

    except Exception as error:
        print(f"⚠️ No se pudo resolver '{artist_name}': {error}")

    if not artist_id:
        artist_id = f"local_{clave.replace(' ', '_')}"

    cache[clave] = artist_id
    return artist_id


def resolver_track_id(cache, track_id, track_name, artist_id):
    """Reutiliza un ID existente para la misma canción y artista."""
    clave = (
        track_name.strip().lower(),
        artist_id,
    )

    if clave not in cache:
        cache[clave] = track_id

    return cache[clave]


def insertar_registro(cursor, row, columnas, artist_id, track_id):
    """Inserta las entidades principales y una reproducción."""
    artist_name = row[columnas["artist"]]
    track_name = row[columnas["track"]]
    played_at = row[columnas["timestamp"]]
    duration_ms = int(row[columnas["duration"]])

    cursor.execute(
        """
        INSERT OR IGNORE INTO artists (
            artist_id,
            artist_name
        )
        VALUES (?, ?)
        """,
        (artist_id, artist_name),
    )

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


def procesar_historial():
    """Carga el historial histórico de Spotify en SQLite."""
    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"No existe la carpeta de datos: {DATA_DIR}"
        )

    df = cargar_jsons(DATA_DIR)

    if df.empty:
        print("⚠️ No se encontraron registros en los JSON.")
        return

    print(f"📊 Registros iniciales: {len(df)}")

    df, columnas = limpiar_historial(df)
    df = preparar_track_ids(df, columnas)

    print(f"🧹 Registros válidos (>30 segundos): {len(df)}")

    inicializar_db()

    spotify = conectar_spotify()
    conn = obtener_conexion()
    cursor = conn.cursor()

    artist_cache = {}
    track_cache = {}
    nuevos_plays = 0

    try:
        for index, row in df.iterrows():
            artist_name = str(row[columnas["artist"]])
            track_name = str(row[columnas["track"]])
            track_id_original = row["track_id"]

            artist_id = resolver_artist_id(
                spotify,
                artist_cache,
                artist_name,
            )

            track_id = resolver_track_id(
                track_cache,
                track_id_original,
                track_name,
                artist_id,
            )

            if insertar_registro(
                cursor,
                row,
                columnas,
                artist_id,
                track_id,
            ):
                nuevos_plays += 1

            if len(artist_cache) % 25 == 0 and len(artist_cache) > 0:
                print(
                    f"   ...{len(artist_cache)} artistas únicos procesados"
                )
                time.sleep(0.05)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    print(
        f"✅ Proceso terminado. "
        f"Se agregaron {nuevos_plays} reproducciones."
    )
    print(
        f"👤 Artistas resueltos/consultados: {len(artist_cache)}"
    )


if __name__ == "__main__":
    procesar_historial()
