"""Análisis sobre los datos de evaluación.

Pandas puro: recibe DataFrames de `queries` y devuelve DataFrames. Sin SQL, sin
matplotlib y sin ReportLab, para que cada análisis se pueda probar solo.
"""

import pandas as pd


#: Niveles a los que se puede aplicar `aporte_por_factor`.
NIVEL_INDICADOR = 'indicador'
NIVEL_SUBINDICADOR = 'subindicador'

_COLUMNAS = {
    NIVEL_INDICADOR: ('indicador_id', 'indicador_nombre'),
    NIVEL_SUBINDICADOR: ('subindicador_id', 'subindicador_nombre'),
}


def _agregar_a_indicador(contribuciones):
    """Colapsa los sub-indicadores en su indicador primario.

    El aporte del indicador es la suma de los de sus sub-indicadores. El valor
    representativo es la media ponderada de sus puntajes por el peso relativo
    dentro del indicador, que queda en la misma escala 1..4.
    """
    df = contribuciones.copy()
    df['valor_ponderado'] = df['valor'] * df['peso_sub']
    agregado = df.groupby(['id_inmueble', 'indicador_id', 'indicador_nombre'], as_index=False).agg(
        contribucion=('contribucion', 'sum'),
        valor=('valor_ponderado', 'sum'),
    )
    return agregado


def aporte_por_factor(contribuciones, nivel=NIVEL_INDICADOR):
    """Cuánto aporta cada indicador (o sub-indicador) al índice de riesgo.

    `nivel` elige la granularidad. Para cada factor calcula su puntaje medio
    (escala 1..4) y qué porcentaje del índice medio explica su aporte
    ponderado. Es la respuesta a "qué factores explican el riesgo", ordenada
    de mayor a menor aporte.
    """
    col_id, col_nombre = _COLUMNAS[nivel]

    if contribuciones.empty:
        return pd.DataFrame(columns=['factor_id', 'factor_nombre', 'valor_medio', 'aporte_pct'])

    datos = _agregar_a_indicador(contribuciones) if nivel == NIVEL_INDICADOR else contribuciones

    indice_medio = datos.groupby('id_inmueble')['contribucion'].sum().mean()

    aporte_medio = datos.groupby(col_id)['contribucion'].mean()
    valor_medio = datos.groupby(col_id)['valor'].mean()
    nombres = datos.drop_duplicates(col_id).set_index(col_id)[col_nombre]

    df = pd.DataFrame({
        'factor_id': aporte_medio.index,
        'factor_nombre': nombres.loc[aporte_medio.index].values,
        'valor_medio': valor_medio.loc[aporte_medio.index].values,
        'aporte_pct': (aporte_medio / indice_medio * 100).values if indice_medio else 0.0,
    })
    return df.sort_values('aporte_pct', ascending=False).reset_index(drop=True)


def resumen_distribucion(indice):
    """Estadística descriptiva del índice: media, mediana, cuartiles y dispersión."""
    serie = indice['indice_de_riesgo']
    if serie.empty:
        return {}
    return {
        'n': int(serie.size),
        'min': float(serie.min()),
        'q1': float(serie.quantile(0.25)),
        'mediana': float(serie.median()),
        'media': float(serie.mean()),
        'q3': float(serie.quantile(0.75)),
        'max': float(serie.max()),
        'desv': float(serie.std()),
    }
