import os
import sqlite3
from datetime import datetime

UMBRAL_SEGUNDOS = 90


def obtener_conexion():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'spotify_data.db')
    return sqlite3.connect(db_path)


def parsear(ts):
    ts = ts.replace('Z', '')
    for fmt in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    raise ValueError(f"No se pudo interpretar la fecha: {ts}")


def deduplicar():
    conn = obtener_conexion()
    cursor = conn.cursor()

    cursor.execute("SELECT play_id, track_id, played_at FROM play_history")
    filas = cursor.fetchall()

    registros = []
    for play_id, track_id, played_at in filas:
        tiempo = parsear(played_at)
        registros.append((track_id, tiempo, play_id))

    registros.sort(key=lambda r: (r[0], r[1]))

    a_borrar = []
    ultimo_track = None
    ultimo_tiempo = None

    for track_id, tiempo, play_id in registros:
        if track_id == ultimo_track and ultimo_tiempo is not None:
            diff = (tiempo - ultimo_tiempo).total_seconds()
            if 0 <= diff <= UMBRAL_SEGUNDOS:
                a_borrar.append(play_id)
                continue
        ultimo_track = track_id
        ultimo_tiempo = tiempo

    print(f"Se encontraron {len(a_borrar)} reproducciones duplicadas (mismo track, <= {UMBRAL_SEGUNDOS}s de diferencia).")

    if a_borrar:
        cursor.executemany("DELETE FROM play_history WHERE play_id = ?", [(pid,) for pid in a_borrar])
        conn.commit()
        print(f"Se borraron {len(a_borrar)} reproducciones duplicadas.")
    else:
        print("No había nada que borrar.")

    conn.close()


if __name__ == "__main__":
    deduplicar()
