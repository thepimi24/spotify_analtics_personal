from collections import defaultdict

from database import obtener_conexion


def agrupar_tracks(rows):
    """Agrupa canciones por nombre normalizado y artista."""
    grupos = defaultdict(list)

    for track_id, track_name, artist_id in rows:
        clave = (
            track_name.strip().lower(),
            artist_id,
        )
        grupos[clave].append(track_id)

    return grupos


def fusionar_tracks_duplicados():
    """Consolida IDs duplicados de una misma canción."""
    conn = obtener_conexion()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT track_id, track_name, artist_id
            FROM tracks
            """
        )

        grupos = agrupar_tracks(cursor.fetchall())

        fusiones = 0
        canciones_afectadas = 0

        for track_ids in grupos.values():
            if len(track_ids) <= 1:
                continue

            canonico = sorted(track_ids)[0]
            canciones_afectadas += 1

            for track_id in track_ids:
                if track_id == canonico:
                    continue

                cursor.execute(
                    """
                    UPDATE play_history
                    SET track_id = ?
                    WHERE track_id = ?
                    """,
                    (canonico, track_id),
                )

                cursor.execute(
                    """
                    DELETE FROM tracks
                    WHERE track_id = ?
                    """,
                    (track_id,),
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
            f"✅ {canciones_afectadas} canciones tenían IDs duplicados."
        )
        print(
            f"   Se consolidaron {fusiones} IDs adicionales."
        )
    else:
        print(
            "✅ No se encontraron canciones duplicadas."
        )


if __name__ == "__main__":
    fusionar_tracks_duplicados()
