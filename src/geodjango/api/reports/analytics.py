"""Análisis sobre los datos de evaluación.

Pandas puro: recibe DataFrames de `queries` y devuelve DataFrames. Sin SQL, sin
matplotlib y sin ReportLab, para que cada análisis se pueda probar solo.

`diagnostico` distingue déficits sistémicos de factores diferenciadores, y se
aplica tanto a los indicadores primarios como a sus sub-indicadores.
"""

import numpy as np
import pandas as pd

from . import niveles


# Clasificación de un sub-indicador según aporte y capacidad de discriminar.
SISTEMICO = 'Sistémico'
DIFERENCIADOR = 'Diferenciador'
SECUNDARIO = 'Secundario'
MENOR = 'Menor'

#: Orden de prioridad para presentar los grupos.
ORDEN_CLASIFICACION = (SISTEMICO, DIFERENCIADOR, SECUNDARIO, MENOR)

DESCRIPCION_CLASIFICACION = {
    SISTEMICO: 'Pesa mucho en el índice pero casi no varía entre inmuebles: '
               'es una carencia del sitio, no de un predio. Se corrige con una '
               'sola intervención programática.',
    DIFERENCIADOR: 'Pesa mucho y además separa unos inmuebles de otros: '
                   'es donde la intervención predio a predio rinde más.',
    SECUNDARIO: 'Discrimina entre inmuebles pero aporta poco al índice: '
                'útil para afinar prioridades, no para moverlas.',
    MENOR: 'Ni pesa ni discrimina de forma relevante en el resultado actual.',
}


#: Niveles a los que se puede aplicar el diagnóstico.
NIVEL_INDICADOR = 'indicador'
NIVEL_SUBINDICADOR = 'subindicador'

_COLUMNAS = {
    NIVEL_INDICADOR: ('indicador_id', 'indicador_nombre'),
    NIVEL_SUBINDICADOR: ('subindicador_id', 'subindicador_nombre'),
}


def _indice_total(contribuciones):
    """Índice de riesgo por inmueble a partir de los aportes ponderados."""
    return contribuciones.groupby('id_inmueble')['contribucion'].sum()


def _agregar_a_indicador(contribuciones):
    """Colapsa los sub-indicadores en su indicador primario.

    El aporte del indicador es la suma de los de sus sub-indicadores. El valor
    representativo es la media ponderada de sus puntajes por el peso relativo
    dentro del indicador, que es el puntaje del indicador en escala 1..4.
    """
    df = contribuciones.copy()
    df['valor_ponderado'] = df['valor'] * df['peso_sub']
    agregado = df.groupby(['id_inmueble', 'indicador_id', 'indicador_nombre'], as_index=False).agg(
        contribucion=('contribucion', 'sum'),
        valor=('valor_ponderado', 'sum'),
        peso_ind=('peso_ind', 'first'),
    )
    agregado['peso_sub'] = 1.0
    return agregado


def diagnostico(contribuciones, umbral_correlacion=0.40, nivel=NIVEL_SUBINDICADOR):
    """Separa déficits sistémicos de factores diferenciadores.

    `nivel` elige la granularidad: los indicadores primarios o sus
    sub-indicadores. El cálculo es el mismo; sólo cambia sobre qué se agrupa.

    Para cada factor calcula:

    - `valor_medio`   promedio del puntaje crudo (1..4)
    - `aporte_pct`    cuánto del índice medio explica su aporte ponderado
    - `correlacion`   correlación de su puntaje con el RESTO del índice
    - `pct_alto`      porcentaje de inmuebles con puntaje 3 o 4
    - `sin_variacion` True si todos los inmuebles puntúan igual

    La correlación se calcula contra el índice menos el aporte del propio
    sub-indicador. Correlacionarlo contra el total completo lo infla, porque el
    total contiene a la parte, y un revisor lo objetaría con razón.

    Un aporte alto con correlación baja significa que casi todos los inmuebles
    puntúan parecido: el problema es del sitio y se resuelve con una sola
    intervención. Un aporte alto con correlación alta significa que el
    sub-indicador separa unos inmuebles de otros y la intervención debe ser
    predio a predio.
    """
    col_id, col_nombre = _COLUMNAS[nivel]

    if contribuciones.empty:
        return pd.DataFrame(columns=[
            'factor_id', 'factor_nombre', 'grupo', 'valor_medio', 'aporte_medio',
            'aporte_pct', 'correlacion', 'pct_alto', 'sin_variacion', 'clasificacion',
        ])

    datos = _agregar_a_indicador(contribuciones) if nivel == NIVEL_INDICADOR else contribuciones

    total = _indice_total(datos)
    indice_medio = total.mean()

    aporte = datos.pivot_table(
        index='id_inmueble', columns=col_id, values='contribucion', aggfunc='sum')
    valor = datos.pivot_table(
        index='id_inmueble', columns=col_id, values='valor', aggfunc='mean')

    columnas_meta = [col_nombre, 'peso_sub', 'peso_ind']
    if nivel == NIVEL_SUBINDICADOR:
        columnas_meta.insert(1, 'indicador_nombre')
    nombres = datos.drop_duplicates(col_id).set_index(col_id)[columnas_meta]

    filas = []
    for sub_id in aporte.columns:
        col_valor = valor[sub_id]
        col_aporte = aporte[sub_id]
        resto = total.reindex(col_aporte.index) - col_aporte

        sin_variacion = bool(col_valor.nunique(dropna=True) <= 1)
        # `corr` sobre una serie constante divide por una desviación cero: da NaN
        # y emite un RuntimeWarning de numpy. Se comprueba antes de llamarla, en
        # ambas series: el "resto" también es constante cuando la amenaza tiene
        # un solo sub-indicador.
        resto_constante = bool(resto.nunique(dropna=True) <= 1)
        if sin_variacion or resto_constante:
            # Un sub-indicador sin variación no es un dato faltante: es el
            # hallazgo sistémico más fuerte posible. Se representa con
            # correlación nula, que es lo que significa "no discrimina".
            correlacion = 0.0
        else:
            correlacion = float(col_valor.corr(resto))
            if np.isnan(correlacion):
                correlacion = 0.0

        meta = nombres.loc[sub_id]
        filas.append({
            'factor_id': int(sub_id),
            'factor_nombre': meta[col_nombre],
            # En el nivel de indicador el factor no pertenece a otro grupo.
            'grupo': meta['indicador_nombre'] if nivel == NIVEL_SUBINDICADOR else '',
            'peso_sub': float(meta['peso_sub']),
            'peso_ind': float(meta['peso_ind']),
            'valor_medio': float(col_valor.mean()),
            'aporte_medio': float(col_aporte.mean()),
            'aporte_pct': float(col_aporte.mean() / indice_medio * 100) if indice_medio else 0.0,
            'correlacion': correlacion,
            'pct_alto': float((col_valor >= 3).mean() * 100),
            'sin_variacion': sin_variacion,
        })

    df = pd.DataFrame(filas)
    df.attrs['nivel'] = nivel
    corte_aporte = df['aporte_pct'].median()

    def clasificar(fila):
        pesa = fila['aporte_pct'] >= corte_aporte
        discrimina = abs(fila['correlacion']) >= umbral_correlacion
        if pesa and not discrimina:
            return SISTEMICO
        if pesa and discrimina:
            return DIFERENCIADOR
        if discrimina:
            return SECUNDARIO
        return MENOR

    df['clasificacion'] = df.apply(clasificar, axis=1)
    df.attrs['corte_aporte'] = float(corte_aporte)
    df.attrs['umbral_correlacion'] = float(umbral_correlacion)
    return df.sort_values('aporte_pct', ascending=False).reset_index(drop=True)


def resumen_distribucion(indice):
    """Estadística descriptiva del índice: hoy el informe sólo publica la media."""
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
