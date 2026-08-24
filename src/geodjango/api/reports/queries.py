"""Consultas a PostGIS para el reporte PDF.

Reutiliza el mismo cálculo de índice de riesgo que las vistas de export
(`api/views.py`): índice del inmueble = SUM( SUM(valor * subindicador.peso) *
indicador.peso ) sobre los indicadores de la amenaza.

Tres granularidades:
- índice total ponderado por inmueble        -> Figura 1 / Tabla 1 / promedios
- puntaje por indicador SIN ponderar (1..4)  -> Figura 2
- valor crudo por subindicador (1..4)        -> Figura 3+
"""

import os

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine


def _engine():
    url = (
        "postgresql://"
        + os.getenv("DATABASE_USER")
        + ":"
        + os.getenv("DATABASE_PASSWORD")
        + "@"
        + os.getenv("DATABASE_HOST")
        + ":"
        + os.getenv("DATABASE_PORT")
        + "/"
        + os.getenv("DATABASE_NAME")
    )
    return create_engine(url)


def amenazas():
    """DataFrame de amenazas: columnas id, nombre (ordenado por id)."""
    sql = "SELECT id, nombre FROM amenazas ORDER BY id"
    with _engine().connect() as con:
        return pd.read_sql(sql, con)


def total_inmuebles():
    """Total de inmuebles del sitio (denominador de los porcentajes)."""
    with _engine().connect() as con:
        return int(pd.read_sql("SELECT COUNT(*) AS n FROM inmuebles", con)["n"].iloc[0])


def inmuebles_geo():
    """GeoDataFrame de TODOS los inmuebles (id_inmueble, geom) en EPSG:3857.

    Sirve de base geográfica: se le hace merge del índice/valor según la
    figura para colorear el mapa.
    """
    sql = "SELECT id AS id_inmueble, geom FROM inmuebles WHERE geom IS NOT NULL"
    with _engine().connect() as con:
        gdf = gpd.read_postgis(sql, con, geom_col="geom")
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    return gdf.to_crs(epsg=3857)


def indice_por_inmueble(amenaza_id):
    """DataFrame [id_inmueble, indice_de_riesgo] (solo inmuebles evaluados)."""
    sql = f"""
        SELECT id_inmueble, SUM(total) AS indice_de_riesgo
        FROM (
            SELECT e.id_inmueble, ind.id AS indicador_id,
                   SUM(e.valor * si.peso) * ind.peso AS total
            FROM evaluacion e
            JOIN sub_indicadores si ON e.id_subindicador = si.id
            JOIN indicadores ind ON si.indicador_id = ind.id
            WHERE ind.amenaza_id = {int(amenaza_id)}
            GROUP BY e.id_inmueble, ind.id, ind.peso
        ) t
        GROUP BY id_inmueble
    """
    with _engine().connect() as con:
        df = pd.read_sql(sql, con)
    df["indice_de_riesgo"] = df["indice_de_riesgo"].astype(float)
    return df


def indicador_scores(amenaza_id):
    """DataFrame [id_inmueble, indicador_id, indicador_nombre, score].

    `score` = SUM(valor * subindicador.peso) SIN multiplicar por el peso del
    indicador -> queda en escala ~1..4 para clasificar por nivel (Figura 2).
    """
    sql = f"""
        SELECT e.id_inmueble, ind.id AS indicador_id, ind.nombre AS indicador_nombre,
               SUM(e.valor * si.peso) AS score
        FROM evaluacion e
        JOIN sub_indicadores si ON e.id_subindicador = si.id
        JOIN indicadores ind ON si.indicador_id = ind.id
        WHERE ind.amenaza_id = {int(amenaza_id)}
        GROUP BY e.id_inmueble, ind.id, ind.nombre
        ORDER BY ind.id
    """
    with _engine().connect() as con:
        df = pd.read_sql(sql, con)
    df["score"] = df["score"].astype(float)
    return df


def subindicador_valores(amenaza_id):
    """DataFrame [id_inmueble, subindicador_id, subindicador_nombre,
    indicador_nombre, valor] con el valor crudo de cada evaluación (Figura 3+)."""
    sql = f"""
        SELECT e.id_inmueble,
               si.id AS subindicador_id, si.nombre AS subindicador_nombre,
               ind.nombre AS indicador_nombre, e.valor
        FROM evaluacion e
        JOIN sub_indicadores si ON e.id_subindicador = si.id
        JOIN indicadores ind ON si.indicador_id = ind.id
        WHERE ind.amenaza_id = {int(amenaza_id)}
        ORDER BY ind.id, si.id
    """
    with _engine().connect() as con:
        df = pd.read_sql(sql, con)
    df["valor"] = df["valor"].astype(float)
    return df


def indicadores(amenaza_id):
    """DataFrame [id, nombre, descripcion] de los indicadores de la amenaza."""
    sql = f"""
        SELECT id, nombre, descripcion
        FROM indicadores
        WHERE amenaza_id = {int(amenaza_id)}
        ORDER BY id
    """
    with _engine().connect() as con:
        return pd.read_sql(sql, con)
