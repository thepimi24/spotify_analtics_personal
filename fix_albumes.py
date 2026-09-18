import sqlite3
from pathlib import Path

# Ruta a tu base de datos
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "spotify_data.db"

def fix_albumes():
    """
    Script de limpieza para unificar sencillos con sus álbumes
    correspondientes en la tabla 'tracks'.
    """
    print("Conectando a la base de datos...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # ============================================================
        # FASE 1: CORRECCIÓN AUTOMÁTICA RELACIONAL
        # ============================================================
        # Actualiza los sencillos si la versión del álbum ya existe
        # en la base de datos bajo el mismo artista.
        
        query_auto = """
            UPDATE tracks
            SET album_name = (
                SELECT t2.album_name
                FROM tracks t2
                WHERE t2.track_name = tracks.track_name
                  AND t2.artist_id = tracks.artist_id
                  AND t2.album_name != t2.track_name
                LIMIT 1
            )
            WHERE album_name = track_name
              AND EXISTS (
                SELECT 1
                FROM tracks t3
                WHERE t3.track_name = tracks.track_name
                  AND t3.artist_id = tracks.artist_id
                  AND t3.album_name != t3.track_name
              );
        """
        
        cursor.execute(query_auto)
        print(f"✔️ FASE 1: {cursor.rowcount} sencillos actualizados automáticamente usando referencias cruzadas.")

        # ============================================================
        # FASE 2: MAPEO MANUAL FORZADO (DICCIONARIO)
        # ============================================================
        # Fuerza la actualización de canciones que no tienen la versión 
        # del álbum en la BD. Puedes agregar tantas como necesites aquí.
        
        mapeo_manual = {
            # "Nombre de la canción (track_name)": "Nombre del álbum destino (album_name)"
            "greda": "Think Later",                   # Caso Tate McRae (según tu registro)
            "greedy": "THINK LATER",                  # Variante ortográfica correcta
            "Animal": "WILD"        # Ejemplo de sencillo que sí debe quedar como sencillo
        }

        print("\nEjecutando Fase 2 (Mapeo Manual)...")
        
        for cancion, album in mapeo_manual.items():
            # Usamos COLLATE NOCASE para que ignore mayúsculas/minúsculas al buscar la canción
            query_manual = """
                UPDATE tracks
                SET album_name = ?
                WHERE track_name = ? COLLATE NOCASE
                  AND album_name != ?
            """
            cursor.execute(query_manual, (album, cancion, album))
            
            if cursor.rowcount > 0:
                print(f"  -> '{cancion}' asignada a '{album}' ({cursor.rowcount} registros corregidos).")

        # ============================================================
        # GUARDAR CAMBIOS
        # ============================================================
        conn.commit()
        print("\n✅ Proceso de limpieza finalizado. Los cambios han sido guardados en 'spotify_data.db'.")

    except sqlite3.Error as e:
        print(f"\n❌ Error de SQLite: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_albumes()