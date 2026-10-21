# spotify_analtics_personal

Un dashboard interactivo desarrollado con Python y Streamlit para analizar un historial personal de reproducciones de Spotify.

Que analiza este dashboard?

- reproducciones totales
- canciones
- artistas
- Top 100 canciones
- Top 10 artistas
- rankings semanales
- rankings mensuales
- rankings anuales
- análisis individual de artistas
- trayectoria de canciones
- rankings de álbumes
- trayectoria de álbumes

Tecnologías Utilizadas:

- Python
- SQLite
  
  Librerias:
    - Pandas
    - Streamlit
    - Altair
    - Spotipy

Que función tiene cada archivo de código que he subido:

- dashboard.py: El principal código de este proyecto, donde se muestran y se visualizan los datos de las canciones, artistas y albumes metricados y los gráficos (charts) puntuales de ciertos análisis.
- database.py: Crea la conexión con la base de datos y crea las tablas si no han sido creadas anteriormente como respaldo de olvido de información.
- etl_batch_json.py: Lee todos los archivos JSON que le pedimos a Spotify que nos de toda la data de las canciones y reproducciones. Extrae esa misma data, limpia las reproducciones incompletas (aquellas que solo tienen menos de 30 segundos de reproducidas) y carga el historial completo de Spotify en SQLite.
- etl_pipeline.py: Conecta la conexión con Spotify, Busca una canción ya normalizada en la base de datos y la guarda en la base de datos y extrae y guarda reproducciones recientes en la base de datos.
- deduplicar_reproducciones.py: Este código evita la doble reproducción de una canción; detecta cuales son las canciones que se han reproducido incompletamente (con un umbral de 90 segundos) y las borra de la base de datos, así esta alineado con la norma de reproducción de Spotify que para cada canción debe reproducirse por lo menos en un 70%,a su vez protegiendo la normalización de los datos.
- extractor.py: Extrae de la API de Spotify el total permitido de 50 canciones para la consulta en la BD.
- diagnostico.py: Detecta las canciones que tienen una mismo nombre y artista pero con diferente ID (ejemplo: Take My Breath - The Weeknd; tiene un id como sencillo y luego tiene otro id como parte del album DAWN FN) y detecta el duplicado si existe y compara la zona horaria para saber si la canción forma parte del conteo en su semana o de otra (solo en casos si el día metricado es el domingo en la noche, huso horario +0)
- enrich_tracks.py: Enriquece cada canción escuchada dentro de su album, siempre detectando si la canción forma parte de un álbum, en bloques de 60 * 60, ya que la data de Spotify no enriquece esa data con los álbumes respectivamente.
- fix_albumes.py: Este un código de limpieza para unificar los sencillos con sus respectivos albumes, para que pueda formar parte de las métricas de los álbumes.
- fix_artist.py: Código de limpieza que resuelve la unificación de los artistas con diferentes ID y funciona duplicados
- fix_track_id.py: Código de limpieza que resuelve la unificación de IDS duplicados de las canciones.
- spotify_listener.py: Al correr este código registra en tiempo real cada canción reproducida en un lapsus de 30 segundos por cada ciclo.

Como ejecutar este proyecto?

LOCALHOST VERSION

- Inicia sesión en Spotify
- Crea una sesión de Spotify Developers.
- Conecta la API de Spotify en su localhost predeterminado.
- Crea el espacio virtual (venv)
- Crea los códigos de los proyectos 
- Ejecuta los códigos del proyecto dentro de su espacio virtual (venv) si no, no ejecutaran.
- Por ultimo, ejecuta el dashboard bajo la librería streamlit: streamlit run dashboard.py

PRODUCTION VERSION

En el siguiente URL: ferspotify.streamlit.app

Podrías ingresar y ver el resultado final del dashboard completo donde se almacena el pipeline de datos.
