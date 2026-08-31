"""Consultas a PostGIS para el informe PDF.

El índice de riesgo se calcula con la fórmula canónica de `api/riesgo.py`
(`INDICE_SQL`), la misma que usan las exportaciones a SHP y KML:

    índice = Σ_indicador [ peso_indicador × Σ_subindicador ( valor × peso_sub ) ]

Tres granularidades:
- índice total ponderado por inmueble        -> Figura 1 / Tabla 1 / promedios
- puntaje por indicador SIN ponderar (1..4)  -> Figura 2
- valor crudo por subindicador (1..4)        -> Figura 3+
"""

import os

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from api import riesgo


_ENGINE = None


def _engine():
    """Engine único del módulo.

    Antes se creaba uno nuevo en cada consulta -siete o más por informe- y
    ninguno se cerraba.

    `NullPool` es deliberado: Celery usa el modelo prefork, y un pool heredado
    al hacer fork comparte sockets entre procesos, lo que produce errores de
    descifrado SSL intermitentes. Sin pool se abre una conexión corta por
    consulta, que para un informe (una decena de consultas) no es problema y es
    seguro frente a fork por construcción.
    """
    global _ENGINE
    if _ENGINE is None:
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
        _ENGINE = create_engine(url, poolclass=NullPool)
    return _ENGINE


def _leer(sql, **params):
    """DataFrame a partir de SQL con parámetros ligados."""
    with _engine().connect() as con:
        return pd.read_sql(text(sql), con, params=params)


def amenazas():
    """DataFrame de amenazas: columnas id, nombre (ordenado por id)."""
    return _leer("SELECT id, nombre FROM amenazas ORDER BY id")


def amenaza(amenaza_id):
    """Fila de una amenaza como dict, o `None` si no existe.

    Permite distinguir "amenaza inexistente" de "amenaza sin evaluaciones", que
    hoy se confunden y terminan produciendo un informe vacío titulado "Incendio".
    """
    df = _leer("SELECT id, nombre, descripcion FROM amenazas WHERE id = :amenaza_id",
               amenaza_id=int(amenaza_id))
    return None if df.empty else df.iloc[0].to_dict()


def total_inmuebles():
    """Total de inmuebles del sitio (denominador de los porcentajes)."""
    return int(_leer("SELECT COUNT(*) AS n FROM inmuebles")["n"].iloc[0])


def inmuebles_meta():
    """Atributos de identificación de cada inmueble, sin geometría."""
    return _leer("""
        SELECT id AS id_inmueble, manzana, predio, rol_sii, direccion
        FROM inmuebles
        ORDER BY id
    """)


def inmuebles_geo():
    """GeoDataFrame de TODOS los inmuebles (id_inmueble, geom) en EPSG:3857.

    Base geográfica común: se le hace merge del índice o del valor según la
    figura, para colorear el mapa.
    """
    sql = "SELECT id AS id_inmueble, geom FROM inmuebles WHERE geom IS NOT NULL"
    with _engine().connect() as con:
        gdf = gpd.read_postgis(sql, con, geom_col="geom")
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    return gdf.to_crs(epsg=3857)


def indice_por_inmueble(amenaza_id):
    """DataFrame [id_inmueble, indice_de_riesgo] (solo inmuebles evaluados)."""
    df = _leer(riesgo.INDICE_SQL, amenaza_id=int(amenaza_id))
    df["indice_de_riesgo"] = df["indice_de_riesgo"].astype(float)
    return df


def indicador_scores(amenaza_id):
    """DataFrame [id_inmueble, indicador_id, indicador_nombre, score].

    `score` = SUM(valor * peso_subindicador) SIN multiplicar por el peso del
    indicador, de modo que queda en escala ~1..4 y es clasificable por nivel.
    """
    df = _leer("""
        SELECT e.id_inmueble, ind.id AS indicador_id, ind.nombre AS indicador_nombre,
               SUM(e.valor * si.peso) AS score
        FROM evaluacion e
        JOIN sub_indicadores si ON e.id_subindicador = si.id
        JOIN indicadores ind ON si.indicador_id = ind.id
        WHERE ind.amenaza_id = :amenaza_id
        GROUP BY e.id_inmueble, ind.id, ind.nombre
        ORDER BY ind.id
    """, amenaza_id=int(amenaza_id))
    df["score"] = df["score"].astype(float)
    return df


def contribuciones(amenaza_id):
    """Aporte ponderado de cada sub-indicador en cada inmueble.

    Superset de la antigua `subindicador_valores`: agrega los pesos y el aporte
    ya multiplicado, lo que permite calcular el aporte por factor sin repetir
    consultas. Incluye la descripción del sub-indicador para enriquecer el
    texto narrativo del informe sin una consulta aparte.

    Columnas: id_inmueble, subindicador_id, subindicador_nombre,
    subindicador_descripcion, indicador_id, indicador_nombre, valor, peso_sub,
    peso_ind, contribucion.
    """
    df = _leer("""
        SELECT e.id_inmueble,
               si.id AS subindicador_id, si.nombre AS subindicador_nombre,
               si.descripcion                        AS subindicador_descripcion,
               ind.id AS indicador_id,   ind.nombre AS indicador_nombre,
               e.valor::numeric                      AS valor,
               si.peso                               AS peso_sub,
               ind.peso                              AS peso_ind,
               e.valor::numeric * si.peso * ind.peso AS contribucion
        FROM evaluacion e
        JOIN sub_indicadores si ON e.id_subindicador = si.id
        JOIN indicadores ind ON si.indicador_id = ind.id
        WHERE ind.amenaza_id = :amenaza_id
        ORDER BY ind.id, si.id
    """, amenaza_id=int(amenaza_id))
    for col in ("valor", "peso_sub", "peso_ind", "contribucion"):
        df[col] = df[col].astype(float)
    return df


def subindicador_valores(amenaza_id):
    """DataFrame [id_inmueble, subindicador_id, subindicador_nombre,
    subindicador_descripcion, indicador_nombre, valor] con el valor crudo de
    cada evaluación (Figura 3+).

    Se deriva de `contribuciones` para no consultar dos veces lo mismo.
    """
    return contribuciones(amenaza_id)[
        ["id_inmueble", "subindicador_id", "subindicador_nombre",
         "subindicador_descripcion", "indicador_nombre", "valor"]
    ]


def indicadores(amenaza_id):
    """DataFrame [id, nombre, descripcion, peso] de los indicadores de la amenaza."""
    return _leer("""
        SELECT id, nombre, descripcion, peso
        FROM indicadores
        WHERE amenaza_id = :amenaza_id
        ORDER BY id
    """, amenaza_id=int(amenaza_id))


def etiquetas_clase(amenaza_id):
    """Etiquetas cualitativas por (subindicador_id, valor).

    Las leyendas de los mapas por sub-indicador muestran hoy "1 / 2 / 3 / 4";
    con esto pueden mostrar "Entramado de madera" o "Continuo 3 paredes".

    Varias clases pueden compartir puntaje dentro de un mismo sub-indicador
    (en Sismo, "Tipo de fundaciones" tiene dos clases de valor 4), de ahí el
    `string_agg`.
    """
    df = _leer("""
        SELECT si.id AS subindicador_id, c.valor,
               string_agg(c.nombre, ' / ' ORDER BY c.id) AS etiqueta
        FROM clases c
        JOIN sub_indicadores si ON c.sub_indicador_id = si.id
        JOIN indicadores ind ON si.indicador_id = ind.id
        WHERE ind.amenaza_id = :amenaza_id AND COALESCE(c.activo, TRUE)
        GROUP BY si.id, c.valor
        ORDER BY si.id, c.valor
    """, amenaza_id=int(amenaza_id))

    salida = {}
    for fila in df.itertuples(index=False):
        salida.setdefault(int(fila.subindicador_id), {})[int(fila.valor)] = fila.etiqueta
    return salida
