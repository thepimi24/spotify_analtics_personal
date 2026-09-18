import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "spotify_data.db"

st.set_page_config(
    page_title="Radar Spotify",
    page_icon="🎧",
    layout="wide",
)


# ============================================================
# CONEXIÓN Y CONSULTAS
# ============================================================

@st.cache_data
def obtener_datos(query, params=()):
    """
    Ejecuta una consulta SQL y devuelve los resultados
    como un DataFrame de pandas.
    """

    conn = sqlite3.connect(DB_PATH)

    try:
        return pd.read_sql_query(
            query,
            conn,
            params=params,
        )
    finally:
        conn.close()


# ============================================================
# FUNCIONES DE FORMATO
# ============================================================

def formatear_numero(valor):
    """
    Convierte un número a un formato más fácil de leer.

    Ejemplo:
        12500 -> 12.500
    """

    if pd.isna(valor):
        return "0"

    return f"{int(valor):,}".replace(",", ".")


def obtener_formato_periodo(periodo_tipo):
    """
    Devuelve el formato de SQLite utilizado para agrupar
    las reproducciones.
    """

    formatos = {
        "Semana": "%Y-W%W",
        "Mes": "%Y-%m",
        "Año": "%Y",
    }

    return formatos[periodo_tipo]


def formatear_periodo(periodo_tipo, valor):
    """
    Convierte períodos internos de SQLite en etiquetas
    más amigables para mostrar en Streamlit.
    """

    meses_cortos = {
        1: "ene",
        2: "feb",
        3: "mar",
        4: "abr",
        5: "may",
        6: "jun",
        7: "jul",
        8: "ago",
        9: "sep",
        10: "oct",
        11: "nov",
        12: "dic",
    }

    meses_largos = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre",
    }

    try:

        if periodo_tipo == "Semana":

            year, week = valor.split("-W")

            monday = datetime.strptime(
                f"{year}-{week}-1",
                "%Y-%W-%w",
            )

            sunday = monday + timedelta(days=6)

            if monday.month == sunday.month:

                return (
                    f"{monday.day} - "
                    f"{sunday.day} "
                    f"{meses_cortos[sunday.month]} "
                    f"{sunday.year}"
                )

            return (
                f"{monday.day} "
                f"{meses_cortos[monday.month]} - "
                f"{sunday.day} "
                f"{meses_cortos[sunday.month]} "
                f"{sunday.year}"
            )

        if periodo_tipo == "Mes":

            year, month = valor.split("-")

            return (
                f"{meses_largos[int(month)]} "
                f"{year}"
            )

        return str(valor)

    except (
        ValueError,
        KeyError,
        AttributeError,
    ):
        return str(valor)


# ============================================================
# MÉTRICAS GENERALES
# ============================================================

def mostrar_metricas_generales():
    """
    Muestra las métricas principales de todo el historial.
    """

    query = """
        SELECT
            COUNT(*) AS reproducciones,
            COUNT(DISTINCT p.track_id) AS canciones,
            COUNT(DISTINCT a.artist_id) AS artistas
        FROM play_history AS p
        INNER JOIN tracks AS t
            ON p.track_id = t.track_id
        INNER JOIN artists AS a
            ON t.artist_id = a.artist_id
    """

    df = obtener_datos(query)

    if df.empty:
        st.warning(
            "No hay datos suficientes para mostrar "
            "las métricas."
        )
        return

    reproducciones = df.loc[0, "reproducciones"]
    canciones = df.loc[0, "canciones"]
    artistas = df.loc[0, "artistas"]

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            label="🎧 Reproducciones",
            value=formatear_numero(
                reproducciones
            ),
        )

    with col2:

        st.metric(
            label="🎵 Canciones",
            value=formatear_numero(
                canciones
            ),
        )

    with col3:

        st.metric(
            label="👤 Artistas",
            value=formatear_numero(
                artistas
            ),
        )


# ============================================================
# TOP 10 ARTISTAS GENERAL
# ============================================================

def mostrar_top_artistas():
    """
    Muestra los 10 artistas con más reproducciones
    de todo el historial.
    """

    query = """
        SELECT
            a.artist_name AS Artista,
            COUNT(p.play_id) AS Reproducciones
        FROM play_history AS p
        INNER JOIN tracks AS t
            ON p.track_id = t.track_id
        INNER JOIN artists AS a
            ON t.artist_id = a.artist_id
        GROUP BY
            a.artist_id,
            a.artist_name
        ORDER BY
            Reproducciones DESC
        LIMIT 10
    """

    df = obtener_datos(query)

    if df.empty:
        st.info(
            "No hay datos de artistas disponibles."
        )
        return

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(
                "Artista:N",
                sort="-y",
                title=None,
                axis=alt.Axis(
                    labelAngle=-35
                ),
            ),
            y=alt.Y(
                "Reproducciones:Q",
                title="Reproducciones",
            ),
            tooltip=[
                alt.Tooltip(
                    "Artista:N",
                    title="Artista",
                ),
                alt.Tooltip(
                    "Reproducciones:Q",
                    title="Reproducciones",
                    format=",",
                ),
            ],
        )
        .properties(
            height=400
        )
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# TOP 100 CANCIONES
# ============================================================

def mostrar_top_100():
    """
    Muestra las 100 canciones con más reproducciones
    de todo el historial.
    """

    query = """
        SELECT
            t.track_name AS Cancion,
            a.artist_name AS Artista,
            COUNT(p.play_id) AS Reproducciones
        FROM play_history AS p
        INNER JOIN tracks AS t
            ON p.track_id = t.track_id
        INNER JOIN artists AS a
            ON t.artist_id = a.artist_id
        GROUP BY
            t.track_id,
            t.track_name,
            a.artist_id,
            a.artist_name
        ORDER BY
            Reproducciones DESC
        LIMIT 100
    """

    df = obtener_datos(query)

    if df.empty:
        st.info(
            "No hay canciones disponibles."
        )
        return

    df.insert(
        0,
        "Posición",
        range(1, len(df) + 1),
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# ANÁLISIS INDIVIDUAL DE ARTISTA
# ============================================================

def mostrar_analisis_artista():
    """
    Permite analizar individualmente un artista.

    Incluye:
    - Reproducciones totales
    - Cantidad de canciones
    - Promedio por canción
    - Top 5 gráfico
    - Tabla completa
    - Trayectoria histórica del artista
    """

    st.subheader(
        "🔍 Análisis por artista"
    )

    artistas_query = """
        SELECT DISTINCT
            a.artist_name
        FROM artists AS a
        INNER JOIN tracks AS t
            ON a.artist_id = t.artist_id
        INNER JOIN play_history AS p
            ON t.track_id = p.track_id
        ORDER BY
            a.artist_name
    """

    artistas = obtener_datos(
        artistas_query
    )

    if artistas.empty:
        st.info(
            "Todavía no hay artistas registrados."
        )
        return

    artista = st.selectbox(
        "Selecciona un artista:",
        artistas["artist_name"].tolist(),
        key="artista_analisis",
    )

    # --------------------------------------------------------
    # RESUMEN DEL ARTISTA
    # --------------------------------------------------------

    query_resumen = """
        SELECT
            COUNT(p.play_id) AS reproducciones,
            COUNT(DISTINCT p.track_id) AS canciones,
            ROUND(
                CAST(
                    COUNT(p.play_id)
                    AS FLOAT
                )
                /
                NULLIF(
                    COUNT(DISTINCT p.track_id),
                    0
                ),
                1
            ) AS promedio_por_cancion
        FROM play_history AS p
        INNER JOIN tracks AS t
            ON p.track_id = t.track_id
        INNER JOIN artists AS a
            ON t.artist_id = a.artist_id
        WHERE
            a.artist_name = ?
    """

    resumen_df = obtener_datos(
        query_resumen,
        (artista,),
    )

    if resumen_df.empty:
        st.warning(
            "No se encontraron datos para este artista."
        )
        return

    resumen = resumen_df.iloc[0]

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Reproducciones",
            formatear_numero(
                resumen["reproducciones"]
            ),
        )

    with col2:

        st.metric(
            "Canciones",
            formatear_numero(
                resumen["canciones"]
            ),
        )

    with col3:

        st.metric(
            "Promedio por canción",
            formatear_numero(
                resumen["promedio_por_cancion"]
            ),
        )

    # --------------------------------------------------------
    # TODAS LAS CANCIONES DEL ARTISTA
    # --------------------------------------------------------

    query_canciones = """
        SELECT
            t.track_id AS Track_ID,
            t.track_name AS Cancion,
            COUNT(p.play_id) AS Reproducciones
        FROM play_history AS p
        INNER JOIN tracks AS t
            ON p.track_id = t.track_id
        INNER JOIN artists AS a
            ON t.artist_id = a.artist_id
        WHERE
            a.artist_name = ?
        GROUP BY
            t.track_id,
            t.track_name
        ORDER BY
            Reproducciones DESC
    """

    df_canciones = obtener_datos(
        query_canciones,
        (artista,),
    )

    if df_canciones.empty:
        st.warning(
            "No hay reproducciones registradas "
            "para este artista."
        )
        return

    # --------------------------------------------------------
    # TOP 5 GRÁFICO
    # --------------------------------------------------------

    st.write(
        "**🔥 Top 5 canciones más reproducidas**"
    )

    df_top5 = df_canciones.head(5).copy()

    chart = (
        alt.Chart(df_top5)
        .mark_bar()
        .encode(
            x=alt.X(
                "Cancion:N",
                sort="-y",
                title=None,
                axis=alt.Axis(
                    labelAngle=-35
                ),
            ),
            y=alt.Y(
                "Reproducciones:Q",
                title="Reproducciones",
            ),
            tooltip=[
                alt.Tooltip(
                    "Cancion:N",
                    title="Canción",
                ),
                alt.Tooltip(
                    "Reproducciones:Q",
                    title="Reproducciones",
                    format=",",
                ),
            ],
        )
        .properties(
            height=400
        )
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )

    # --------------------------------------------------------
    # TABLA COMPLETA
    # --------------------------------------------------------

    st.write(
        "**📋 Todas las canciones reproducidas "
        "del artista**"
    )

    tabla = df_canciones.drop(
        columns=["Track_ID"]
    ).copy()

    tabla.insert(
        0,
        "Posición",
        range(
            1,
            len(tabla) + 1
        ),
    )

    st.dataframe(
        tabla,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # TRAYECTORIA DEL ARTISTA
    # --------------------------------------------------------

    mostrar_trayectoria_artista(artista, df_canciones)


# ============================================================
# PERÍODOS DISPONIBLES
# ============================================================

def obtener_periodos(periodo_tipo):
    """
    Obtiene todos los períodos disponibles
    en el historial.
    """

    formato = obtener_formato_periodo(
        periodo_tipo
    )

    query = f"""
        SELECT DISTINCT
            strftime(
                '{formato}',
                p.played_at
            ) AS periodo
        FROM play_history AS p
        WHERE
            p.played_at IS NOT NULL
        ORDER BY
            periodo DESC
    """

    df = obtener_datos(query)

    return (
        df["periodo"]
        .dropna()
        .tolist()
    )


# ============================================================
# ARTISTAS POR SEMANA / MES / AÑO
# ============================================================

def mostrar_artistas_por_periodo():
    """
    Muestra el ranking de artistas por:
    - Semana
    - Mes
    - Año
    """

    st.subheader(
        "🏆 Artistas más escuchados por período"
    )

    col1, col2 = st.columns(2)

    with col1:

        periodo_tipo = st.radio(
            "Agrupar por:",
            [
                "Semana",
                "Mes",
                "Año",
            ],
            horizontal=True,
            key="artistas_periodo_tipo",
        )

    with col2:

        cantidad = st.radio(
            "Mostrar:",
            [
                10,
                20,
            ],
            horizontal=True,
            format_func=lambda x: f"Top {x}",
            key="artistas_periodo_cantidad",
        )

    periodos = obtener_periodos(
        periodo_tipo
    )

    if not periodos:
        st.info(
            "Todavía no hay suficientes datos."
        )
        return

    periodo = st.selectbox(
        f"Selecciona {periodo_tipo.lower()}:",
        periodos,
        format_func=lambda value: formatear_periodo(
            periodo_tipo,
            value,
        ),
        key="artistas_periodo_selector",
    )

    formato = obtener_formato_periodo(
        periodo_tipo
    )

    query = f"""
        SELECT
            a.artist_name AS Artista,
            COUNT(p.play_id) AS Reproducciones
        FROM play_history AS p
        INNER JOIN tracks AS t
            ON p.track_id = t.track_id
        INNER JOIN artists AS a
            ON t.artist_id = a.artist_id
        WHERE
            strftime(
                '{formato}',
                p.played_at
            ) = ?
        GROUP BY
            a.artist_id,
            a.artist_name
        ORDER BY
            Reproducciones DESC
        LIMIT ?
    """

    df = obtener_datos(
        query,
        (
            periodo,
            cantidad,
        ),
    )

    if df.empty:
        st.info(
            "No existen reproducciones "
            "para este período."
        )
        return

    df.insert(
        0,
        "Posición",
        range(
            1,
            len(df) + 1
        ),
    )

    st.write(
        f"**Top {cantidad} artistas — "
        f"{formatear_periodo(periodo_tipo, periodo)}**"
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(
                "Artista:N",
                sort="-y",
                title=None,
                axis=alt.Axis(
                    labelAngle=-45
                ),
            ),
            y=alt.Y(
                "Reproducciones:Q",
                title="Reproducciones",
            ),
            tooltip=[
                alt.Tooltip(
                    "Posición:Q",
                    title="Posición",
                ),
                alt.Tooltip(
                    "Artista:N",
                    title="Artista",
                ),
                alt.Tooltip(
                    "Reproducciones:Q",
                    title="Reproducciones",
                    format=",",
                ),
            ],
        )
        .properties(
            height=450
        )
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# TOP 25 POR PERÍODO
# ============================================================

def mostrar_chart_por_periodo():
    """
    Muestra el Top 25 de canciones para un período.
    """

    st.subheader(
        "📅 Top 25 por período"
    )

    periodo_tipo = st.radio(
        "Agrupar por:",
        [
            "Semana",
            "Mes",
            "Año",
        ],
        horizontal=True,
        key="top25_periodo_tipo",
    )

    periodos = obtener_periodos(
        periodo_tipo
    )

    if not periodos:
        st.info(
            "Todavía no hay suficientes datos."
        )
        return

    periodo = st.selectbox(
        f"Selecciona {periodo_tipo.lower()}:",
        periodos,
        format_func=lambda value: formatear_periodo(
            periodo_tipo,
            value,
        ),
        key="top25_periodo_selector",
    )

    formato = obtener_formato_periodo(
        periodo_tipo
    )

    query = f"""
        SELECT
            t.track_name AS Cancion,
            a.artist_name AS Artista,
            COUNT(p.play_id) AS Reproducciones
        FROM play_history AS p
        INNER JOIN tracks AS t
            ON p.track_id = t.track_id
        INNER JOIN artists AS a
            ON t.artist_id = a.artist_id
        WHERE
            strftime(
                '{formato}',
                p.played_at
            ) = ?
        GROUP BY
            t.track_id,
            t.track_name,
            a.artist_id,
            a.artist_name
        ORDER BY
            Reproducciones DESC
        LIMIT 25
    """

    df = obtener_datos(
        query,
        (periodo,),
    )

    if df.empty:
        st.info(
            "No existen reproducciones "
            "para este período."
        )
        return

    df.insert(
        0,
        "Posición",
        range(
            1,
            len(df) + 1
        ),
    )

    st.write(
        f"**Top 25 — "
        f"{formatear_periodo(periodo_tipo, periodo)}**"
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    st.write(
        "**🔥 Top 10 del período**"
    )

    df_top10 = df.head(10).copy()

    chart = (
        alt.Chart(df_top10)
        .mark_bar()
        .encode(
            x=alt.X(
                "Cancion:N",
                sort="-y",
                title=None,
                axis=alt.Axis(
                    labelAngle=-45
                ),
            ),
            y=alt.Y(
                "Reproducciones:Q",
                title="Reproducciones",
            ),
            tooltip=[
                alt.Tooltip(
                    "Posición:Q",
                    title="Posición",
                ),
                alt.Tooltip(
                    "Cancion:N",
                    title="Canción",
                ),
                alt.Tooltip(
                    "Artista:N",
                    title="Artista",
                ),
                alt.Tooltip(
                    "Reproducciones:Q",
                    title="Reproducciones",
                    format=",",
                ),
            ],
        )
        .properties(
            height=400
        )
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )

    mostrar_trayectoria(
        df,
        periodo_tipo,
    )


# ============================================================
# TRAYECTORIA DE UNA CANCIÓN DEL TOP 25
# ============================================================

def mostrar_trayectoria(
    df_top25,
    periodo_tipo,
):
    """
    Muestra la evolución histórica de una canción
    seleccionada del Top 25.
    """

    st.write(
        "**📈 Trayectoria de una canción**"
    )

    opciones = (
        df_top25["Cancion"]
        + " — "
        + df_top25["Artista"]
    ).tolist()

    if not opciones:
        return

    seleccion = st.selectbox(
        "Elige una canción del Top 25:",
        opciones,
        key=f"trayectoria_{periodo_tipo}",
    )

    indice = opciones.index(
        seleccion
    )

    cancion = (
        df_top25
        .iloc[indice]["Cancion"]
    )

    artista = (
        df_top25
        .iloc[indice]["Artista"]
    )

    query_track = """
        SELECT
            t.track_id AS Track_ID
        FROM tracks AS t
        INNER JOIN artists AS a
            ON t.artist_id = a.artist_id
        WHERE
            t.track_name = ?
            AND a.artist_name = ?
        LIMIT 1
    """

    track_df = obtener_datos(
        query_track,
        (
            cancion,
            artista,
        ),
    )

    if track_df.empty:
        st.warning(
            "No se encontró el ID de la canción."
        )
        return

    track_id = (
        track_df
        .iloc[0]["Track_ID"]
    )

    formato = obtener_formato_periodo(
        periodo_tipo
    )

    query = f"""
        WITH conteos AS (
            SELECT
                strftime(
                    '{formato}',
                    p.played_at
                ) AS periodo,
                p.track_id AS track_id,
                COUNT(*) AS reproducciones
            FROM play_history AS p
            GROUP BY
                periodo,
                p.track_id
        ),

        ranking AS (
            SELECT
                periodo,
                track_id,
                reproducciones,
                ROW_NUMBER() OVER (
                    PARTITION BY periodo
                    ORDER BY
                        reproducciones DESC
                ) AS posicion
            FROM conteos
        )

        SELECT
            periodo,
            posicion,
            reproducciones
        FROM ranking
        WHERE
            track_id = ?
        ORDER BY
            periodo
    """

    df_trayectoria = obtener_datos(
        query,
        (track_id,),
    )

    if len(df_trayectoria) < 2:

        st.info(
            "Todavía no hay suficientes períodos "
            "para mostrar una trayectoria."
        )
        return

    df_trayectoria["Periodo"] = (
        df_trayectoria["periodo"]
        .apply(
            lambda value: formatear_periodo(
                periodo_tipo,
                value,
            )
        )
    )

    mejor_posicion = int(
        df_trayectoria["posicion"].min()
    )

    st.caption(
        f"Mejor posición histórica: "
        f"**#{mejor_posicion}**"
    )

    chart = (
        alt.Chart(df_trayectoria)
        .mark_line(
            point=alt.OverlayMarkDef(
                filled=True,
                size=90,
            )
        )
        .encode(
            x=alt.X(
                "Periodo:N",
                sort=None,
                title=periodo_tipo,
            ),
            y=alt.Y(
                "posicion:Q",
                scale=alt.Scale(
                    reverse=True
                ),
                title="Posición",
                axis=alt.Axis(
                    tickMinStep=1
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "Periodo:N",
                    title="Período",
                ),
                alt.Tooltip(
                    "posicion:Q",
                    title="Posición",
                ),
                alt.Tooltip(
                    "reproducciones:Q",
                    title="Reproducciones",
                    format=",",
                ),
            ],
        )
        .properties(
            height=380
        )
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# TRAYECTORIA HISTÓRICA DEL ARTISTA
# ============================================================

def mostrar_trayectoria_artista(artista, df_canciones_artista):
    """
    Muestra la trayectoria de una canción elegida
    dentro del chart global.
    """

    st.divider()

    st.subheader(
        f"📈 Trayectoria en el chart — {artista}"
    )

    st.markdown(
        """
        Aquí puedes seleccionar una canción para ver cómo se 
        ha comportado dentro de mi ranking general.

        La posición representa el lugar real que ocupó
        cada canción frente a TODAS las canciones del período.
        """
    )

    col1, col2 = st.columns(2)

    with col1:

        periodo_tipo = st.selectbox(
            "Período:",
            [
                "Semana",
                "Mes",
                "Año",
            ],
            key=(
                f"trayectoria_artista_periodo_"
                f"{artista}"
            ),
        )

    with col2:
        
        lista_canciones = df_canciones_artista["Cancion"].tolist()

        cancion_seleccionada = st.selectbox(
            "Seleccionar canción:",
            lista_canciones,
            key=(
                f"trayectoria_artista_cancion_"
                f"{artista}"
            ),
        )

    formato = obtener_formato_periodo(
        periodo_tipo
    )

    track_ids_artista = (
        df_canciones_artista["Track_ID"]
        .tolist()
    )

    if not track_ids_artista:
        return

    query = f"""
        WITH reproducciones AS (
            SELECT
                strftime(
                    '{formato}',
                    p.played_at
                ) AS periodo,
                p.track_id AS track_id,
                t.track_name AS cancion,
                COUNT(p.play_id) AS plays
            FROM play_history AS p
            INNER JOIN tracks AS t
                ON p.track_id = t.track_id
            INNER JOIN artists AS a
                ON t.artist_id = a.artist_id
            GROUP BY
                periodo,
                p.track_id,
                t.track_name
        ),

        ranking AS (
            SELECT
                periodo,
                track_id,
                cancion,
                plays,
                ROW_NUMBER() OVER (
                    PARTITION BY periodo
                    ORDER BY
                        plays DESC,
                        track_id
                ) AS posicion
            FROM reproducciones
        )

        SELECT
            periodo,
            track_id,
            cancion,
            plays,
            posicion
        FROM ranking
        ORDER BY
            periodo,
            posicion
    """

    df_global = obtener_datos(
        query
    )

    if df_global.empty:

        st.info(
            "No existen datos históricos "
            "para construir el chart."
        )
        return

    df_filtrado = df_global[
        df_global["cancion"] == cancion_seleccionada
    ].copy()

    if df_filtrado.empty:
        st.info(
            "Esta canción no logró entrar al ranking global "
            "en ninguno de estos períodos."
        )
        return

    df_filtrado["Periodo"] = (
        df_filtrado["periodo"]
        .apply(
            lambda value: formatear_periodo(
                periodo_tipo,
                value,
            )
        )
    )

    mejor_posicion = int(
        df_filtrado["posicion"].min()
    )

    periodos_chart = (
        df_filtrado["periodo"]
        .nunique()
    )

    periodos_top10 = (
        df_filtrado[df_filtrado["posicion"] <= 10]["periodo"]
        .nunique()
    )

    periodos_numero_1 = (
        df_filtrado[df_filtrado["posicion"] == 1]["periodo"]
        .nunique()
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Mejor posición",
            f"#{mejor_posicion}",
        )

    with col2:

        st.metric(
            "Períodos en chart",
            formatear_numero(
                periodos_chart
            ),
        )

    with col3:

        st.metric(
            "Períodos Top 10",
            formatear_numero(
                periodos_top10
            ),
        )

    with col4:

        st.metric(
            "Períodos #1",
            formatear_numero(
                periodos_numero_1
            ),
        )

    st.write(
        f"**📊 Trayectoria — {cancion_seleccionada}**"
    )

    base = alt.Chart(
        df_filtrado
    )

    lineas = (
        base
        .mark_line(
            color="#E50914",
            point=alt.OverlayMarkDef(
                filled=True,
                size=65,
                color="#E50914"
            )
        )
        .encode(
            x=alt.X(
                "Periodo:N",
                sort=None,
                title=periodo_tipo,
            ),

            y=alt.Y(
                "posicion:Q",
                scale=alt.Scale(
                    reverse=True
                ),
                title="Posición en el chart",
                axis=alt.Axis(
                    tickMinStep=1
                ),
            ),

            tooltip=[
                alt.Tooltip(
                    "cancion:N",
                    title="Canción",
                ),
                alt.Tooltip(
                    "Periodo:N",
                    title="Período",
                ),
                alt.Tooltip(
                    "posicion:Q",
                    title="Posición",
                ),
                alt.Tooltip(
                    "plays:Q",
                    title="Reproducciones",
                    format=",",
                ),
            ],
        )
    )

    st.altair_chart(
        lineas.properties(
            height=500
        ),
        use_container_width=True,
    )


# ============================================================
# ============================================================
# 💿 ÁLBUMES POR SEMANA / MES / AÑO
# ============================================================
# ============================================================

# ============================================================
# ÁLBUMES MÁS ESCUCHADOS POR PERÍODO
# ============================================================

def mostrar_albumes_por_periodo():
    """
    Muestra los álbumes más reproducidos por Semana, Mes o Año.
    Usa una CTE para determinar la fecha oficial de salida del álbum
    completo y evitar que los streams de sencillos previos se filtren.
    """

    st.subheader(
        "💿 Álbumes más escuchados por período"
    )

    col1, col2 = st.columns(2)

    with col1:
        periodo_tipo = st.radio(
            "Agrupar por:",
            ["Semana", "Mes", "Año"],
            horizontal=True,
            key="albumes_periodo_tipo",
        )

    with col2:
        cantidad = st.radio(
            "Mostrar:",
            [10, 20],
            horizontal=True,
            format_func=lambda x: f"Top {x}",
            key="albumes_periodo_cantidad",
        )

    periodos = obtener_periodos(periodo_tipo)

    if not periodos:
        st.info("Todavía no hay suficientes datos para mostrar álbumes.")
        return

    periodo = st.selectbox(
        f"Selecciona {periodo_tipo.lower()}:",
        periodos,
        format_func=lambda value: formatear_periodo(periodo_tipo, value),
        key="albumes_periodo_selector",
    )

    formato = obtener_formato_periodo(periodo_tipo)

    query = f"""
        WITH album_dates AS (
            -- Ahora buscamos la fecha oficial basándonos en el NOMBRE y el ARTISTA
            SELECT 
                album_name,
                artist_id,
                MAX(album_release_date) AS official_release_date
            FROM tracks
            WHERE album_name IS NOT NULL
            GROUP BY album_name, artist_id
        )
        SELECT
            MIN(t.album_id) AS album_id, 
            a.artist_id,
            t.album_name AS Album,
            a.artist_name AS Artista,
            COUNT(p.play_id) AS Reproducciones
        FROM play_history AS p
        INNER JOIN tracks AS t
            ON p.track_id = t.track_id
        INNER JOIN artists AS a
            ON t.artist_id = a.artist_id
        -- El JOIN ahora se conecta mediante el nombre del álbum y el ID del artista
        INNER JOIN album_dates AS ad
            ON t.album_name = ad.album_name AND t.artist_id = ad.artist_id
        WHERE
            strftime('{formato}', p.played_at) = ?
            AND t.album_id IS NOT NULL
            
            -- El filtro ahora evalúa contra la fecha más reciente de cualquier track que comparta el nombre del álbum
            AND strftime('{formato}', p.played_at) >= strftime('{formato}', ad.official_release_date)
            
            AND EXISTS (
                SELECT 1 FROM tracks t3
                WHERE t3.album_id = t.album_id
                  AND t3.track_name != t3.album_name
            )
        GROUP BY
            t.album_name,
            a.artist_name,
            a.artist_id
        ORDER BY
            Reproducciones DESC
        LIMIT ?
    """

    df = obtener_datos(
        query,
        (periodo, cantidad,),
    )

    if df.empty:
        st.info("No existen reproducciones de álbumes para este período.")
        return

    df.insert(0, "Posición", range(1, len(df) + 1))
    
    df_visual = df.drop(columns=["album_id", "artist_id"])

    st.write(
        f"**Top {cantidad} álbumes — "
        f"{formatear_periodo(periodo_tipo, periodo)}**"
    )

    st.dataframe(
        df_visual,
        use_container_width=True,
        hide_index=True,
    )

    st.write("**📊 Ranking de álbumes**")

    chart = (
        alt.Chart(df_visual)
        .mark_bar(color="gold")
        .encode(
            x=alt.X("Reproducciones:Q", title="Reproducciones"),
            y=alt.Y("Album:N", sort="-x", title=None, axis=alt.Axis(labelLimit=250)),
            tooltip=[
                alt.Tooltip("Posición:Q", title="Posición"),
                alt.Tooltip("Album:N", title="Álbum"),
                alt.Tooltip("Artista:N", title="Artista"),
                alt.Tooltip("Reproducciones:Q", title="Reproducciones", format=","),
            ],
        )
        .properties(
            height=max(400, len(df_visual) * 35)
        )
    )

    st.altair_chart(chart, use_container_width=True)

    mostrar_trayectoria_album(df, periodo_tipo)


# ============================================================
# TRAYECTORIA HISTÓRICA DE ÁLBUMES
# ============================================================

def mostrar_trayectoria_album(df_albumes, periodo_tipo):
    """
    Muestra la trayectoria histórica de un álbum
    dentro del ranking GLOBAL utilizando sus IDs nativos
    y respetando la fecha oficial de lanzamiento del proyecto completo.
    """

    st.write("**📈 Trayectoria histórica de un álbum**")

    opciones = (
        df_albumes["Album"]
        + " — "
        + df_albumes["Artista"]
    ).tolist()

    if not opciones:
        return

    seleccion = st.selectbox(
        "Elige un álbum:",
        opciones,
        key=f"trayectoria_album_{periodo_tipo}",
    )

    indice = opciones.index(seleccion)

    album_id = df_albumes.iloc[indice]["album_id"]
    artist_id = df_albumes.iloc[indice]["artist_id"]
    album_nombre = df_albumes.iloc[indice]["Album"]
    artista_nombre = df_albumes.iloc[indice]["Artista"]

    formato = obtener_formato_periodo(periodo_tipo)

    query = f"""
        WITH album_dates AS (
            SELECT 
                album_id, 
                MAX(album_release_date) AS official_release_date
            FROM tracks
            WHERE album_id IS NOT NULL
            GROUP BY album_id
        ),
        reproducciones AS (
            SELECT
                strftime('{formato}', p.played_at) AS periodo,
                t.album_id,
                a.artist_id,
                t.album_name AS album,
                a.artist_name AS artista,
                COUNT(p.play_id) AS plays
            FROM play_history AS p
            INNER JOIN tracks AS t
                ON p.track_id = t.track_id
            INNER JOIN artists AS a
                ON t.artist_id = a.artist_id
            INNER JOIN album_dates AS ad
                ON t.album_id = ad.album_id
            WHERE 
                t.album_id IS NOT NULL
                
                -- Se restringe desde la fecha oficial del álbum completo
                AND strftime('{formato}', p.played_at) >= strftime('{formato}', ad.official_release_date)
                
                -- Se mantiene el filtro anti-sencillos
                AND EXISTS (
                    SELECT 1 FROM tracks t3
                    WHERE t3.album_id = t.album_id
                      AND t3.track_name != t3.album_name
                )
            GROUP BY
                periodo,
                t.album_id,
                a.artist_id,
                t.album_name,
                a.artist_name
        ),
        ranking AS (
            SELECT
                periodo,
                album_id,
                artist_id,
                plays,
                ROW_NUMBER() OVER (
                    PARTITION BY periodo
                    ORDER BY plays DESC, artista, album
                ) AS posicion
            FROM reproducciones
        )
        SELECT
            periodo,
            plays,
            posicion
        FROM ranking
        WHERE
            album_id = ?
            AND artist_id = ?
        ORDER BY
            periodo
    """

    df_trayectoria = obtener_datos(
        query,
        (album_id, artist_id,),
    )

    if df_trayectoria.empty:
        st.info("Este álbum todavía no tiene suficientes datos históricos.")
        return

    df_trayectoria["Periodo"] = (
        df_trayectoria["periodo"]
        .apply(lambda value: formatear_periodo(periodo_tipo, value))
    )

    mejor_posicion = int(df_trayectoria["posicion"].min())
    periodos_chart = df_trayectoria["periodo"].nunique()
    periodos_top10 = df_trayectoria[df_trayectoria["posicion"] <= 10]["periodo"].nunique()
    periodos_numero_1 = df_trayectoria[df_trayectoria["posicion"] == 1]["periodo"].nunique()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Mejor posición", f"#{mejor_posicion}")
    with col2:
        st.metric("Períodos en chart", formatear_numero(periodos_chart))
    with col3:
        st.metric("Períodos Top 10", formatear_numero(periodos_top10))
    with col4:
        st.metric("Períodos #1", formatear_numero(periodos_numero_1))

    chart = (
        alt.Chart(df_trayectoria)
        .mark_line(
            point=alt.OverlayMarkDef(filled=True, size=90)
        )
        .encode(
            x=alt.X("Periodo:N", sort=None, title=periodo_tipo),
            y=alt.Y(
                "posicion:Q",
                scale=alt.Scale(reverse=True),
                title="Posición en el chart",
                axis=alt.Axis(tickMinStep=1),
            ),
            tooltip=[
                alt.Tooltip("Periodo:N", title="Período"),
                alt.Tooltip("posicion:Q", title="Posición"),
                alt.Tooltip("plays:Q", title="Reproducciones", format=","),
            ],
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)

    st.caption(
        f"Trayectoria de **{album_nombre}** de **{artista_nombre}**. "
        f"Las posiciones corresponden al ranking global de álbumes."
    )


# ============================================================
# MÉTRICAS GENERALES
# ============================================================

mostrar_metricas_generales()

st.divider()


# ============================================================
# TOP ARTISTAS + TOP 100
# ============================================================

col1, col2 = st.columns(
    [1, 1.5]
)

with col1:

    st.subheader(
        "🏆 Top 10 artistas"
    )

    mostrar_top_artistas()


with col2:

    st.subheader(
        "🔥 Top 100 canciones"
    )

    mostrar_top_100()


st.divider()


# ============================================================
# ANÁLISIS POR ARTISTA
# ============================================================

mostrar_analisis_artista()

st.divider()


# ============================================================
# ARTISTAS POR SEMANA / MES / AÑO
# ============================================================

mostrar_artistas_por_periodo()

st.divider()


# ============================================================
# TOP 25 POR SEMANA / MES / AÑO
# ============================================================

mostrar_chart_por_periodo()

st.divider()


# ============================================================
# 💿 ÁLBUMES POR SEMANA / MES / AÑO
# ============================================================

mostrar_albumes_por_periodo()