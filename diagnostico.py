from database import obtener_conexion


def crear_indices(conn):
    """Crea índices útiles para las consultas analíticas."""
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_play_history_track_id
            ON play_history(track_id);

        CREATE INDEX IF NOT EXISTS idx_play_history_played_at
            ON play_history(played_at);

        CREATE INDEX IF NOT EXISTS idx_tracks_artist_id
            ON tracks(artist_id);
        """
    )
    conn.commit()


def revisar_canciones_duplicadas(conn):
    """Detecta canciones con el mismo nombre y artista pero distintos IDs."""
    query = """
        WITH conteos AS (
            SELECT track_id, COUNT(*) AS reproducciones
            FROM play_history
            GROUP BY track_id
        )
        SELECT
            LOWER(TRIM(t.track_name)) AS nombre_normalizado,
            a.artist_name,
            COUNT(DISTINCT t.track_id) AS ids_distintos,
            GROUP_CONCAT(t.track_id) AS track_ids,
            SUM(COALESCE(c.reproducciones, 0)) AS total_reproducciones
        FROM tracks t
        JOIN artists a
            ON t.artist_id = a.artist_id
        LEFT JOIN conteos c
            ON c.track_id = t.track_id
        GROUP BY nombre_normalizado, t.artist_id
        HAVING ids_distintos > 1
        ORDER BY total_reproducciones DESC
    """

    rows = conn.execute(query).fetchall()

    if not rows:
        print(
            "✅ No se encontraron canciones con múltiples track_id."
        )
        return

    print(
        f"⚠️ Se encontraron {len(rows)} posibles duplicados:"
    )

    for nombre, artista, cantidad, ids, total in rows:
        print(
            f"- '{nombre}' — {artista}: "
            f"{cantidad} IDs → {total} reproducciones"
        )


def revisar_semana(conn, fecha_inicio, fecha_fin):
    """Compara la agrupación semanal UTC y hora local."""
    query = """
        SELECT
            p.played_at,
            strftime('%Y-%m-%d %H:%M', p.played_at) AS utc,
            strftime(
                '%Y-%m-%d %H:%M',
                p.played_at,
                'localtime'
            ) AS local,
            strftime('%Y-W%W', p.played_at) AS semana_utc,
            strftime(
                '%Y-W%W',
                p.played_at,
                'localtime'
            ) AS semana_local,
            t.track_name
        FROM play_history p
        JOIN tracks t
            ON p.track_id = t.track_id
        WHERE date(p.played_at) BETWEEN ? AND ?
        ORDER BY p.played_at
    """

    rows = conn.execute(
        query,
        (fecha_inicio, fecha_fin),
    ).fetchall()

    print(
        f"\n📅 Reproducciones encontradas: {len(rows)}"
    )

    for played_at, utc, local, semana_utc, semana_local, track in rows:
        aviso = (
            " ⚠️ Semana distinta por huso horario"
            if semana_utc != semana_local
            else ""
        )

        print(
            f"{played_at} | UTC: {utc} ({semana_utc}) | "
            f"Local: {local} ({semana_local}) | {track}{aviso}"
        )


if __name__ == "__main__":
    conn = obtener_conexion()

    try:
        print("⏳ Revisando índices...")
        crear_indices(conn)

        print("\n=== Canciones duplicadas ===")
        revisar_canciones_duplicadas(conn)

        print("\n=== Revisión de semanas ===")
        revisar_semana(
            conn,
            "2026-09-01",
            "2026-09-05",
        )

    finally:
        conn.close()

    print("\n✅ Diagnóstico terminado.")
