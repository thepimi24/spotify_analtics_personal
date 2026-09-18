import os

import pandas as pd
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth


load_dotenv(override=True)

SPOTIFY_SCOPE = "user-read-recently-played"


def conectar_spotify():
    """Autentica el proyecto y devuelve un cliente de Spotify."""
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

    if not client_id or not client_secret or not redirect_uri:
        raise ValueError(
            "No se encontraron las credenciales completas de Spotify. "
            "Revisa SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET y "
            "SPOTIPY_REDIRECT_URI en tu archivo .env."
        )

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SPOTIFY_SCOPE,
    )

    return spotipy.Spotify(auth_manager=auth_manager)


def obtener_recientes(limit=50):
    """Obtiene las últimas reproducciones disponibles en Spotify."""
    spotify = conectar_spotify()
    resultado = spotify.current_user_recently_played(limit=limit)

    registros = []

    for item in resultado.get("items", []):
        track = item["track"]
        artista = track["artists"][0]

        registros.append(
            {
                "played_at": item["played_at"],
                "track_id": track["id"],
                "track_name": track["name"],
                "artist_id": artista["id"],
                "artist_name": artista["name"],
                "duration_ms": track["duration_ms"],
            }
        )

    return pd.DataFrame(registros)


if __name__ == "__main__":
    try:
        df_recientes = obtener_recientes()
        print(f"✅ Se extrajeron {len(df_recientes)} reproducciones.")
        print(df_recientes.head())
    except Exception as error:
        print(f"❌ Ocurrió un error: {error}")
