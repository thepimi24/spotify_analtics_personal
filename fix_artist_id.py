import re

from database import obtener_conexion


def es_id_real_spotify(artist_id):
    """Comprueba si el valor tiene el formato habitual de un ID de Spotify."""
    return bool(re.fullmatch(r"[A-Za-z0-9]{22}", artist_id or ""))


def agrupar_artistas(artistas):
    """Agrupa artistas por nombre normalizado."""
    grupos = {}

    for artist_id, artist_name in artistas:
        clave = artist_name.strip().lower()
        grupos.setdefault(clave, []).append(
            (artist_id, artist_name)
        )

    return grupos


def elegir_artist_id_canonico(entradas):
    """Prefiere un ID real de Spotify; si no existe, usa el primero."""
    for artist_id, _ in entradas:
        if es_id_real_spotify(artist_id):
            return artist_id

    return entradas[0][0]


def fusionar_duplicados():
    """Une artistas duplicados y actualiza sus canciones."""
    conn = obtener_conexion()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT artist_id, artist_name FROM artists"
        )
        grupos = agrupar_artistas(cursor.fetchall())

        fusiones = 0

        for entradas in grupos.values():
            if len(entradas) <= 1:
                continue

            canonico = elegir_artist_id_canonico(entradas)

            for artist_id, artist_name in entradas:
                if artist_id == canonico:
                    continue

                print(
                    f"🔗 Fusionando '{artist_name}' "
                    f"({artist_id}) → {canonico}"
                )

                cursor.execute(
                    """
                    UPDATE tracks
                    SET artist_id = ?
                    WHERE artist_id = ?
                    """,
                    (canonico, artist_id),
                )

                cursor.execute(
                    """
                    DELETE FROM artists
                    WHERE artist_id = ?
                    """,
                    (artist_id,),
                )

                fusiones += 1

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    if fusiones:
        print(
            f"✅ Se fusionaron {fusiones} registros de artistas."
        )
    else:
        print(
            "✅ No se encontraron artistas duplicados."
        )


if __name__ == "__main__":
    fusionar_duplicados()
