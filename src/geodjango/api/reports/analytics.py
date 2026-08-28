"""Análisis sobre los datos de evaluación.

Pandas puro: recibe DataFrames de `queries` y devuelve DataFrames. Sin SQL, sin
matplotlib y sin ReportLab, para que cada análisis se pueda probar solo.

Cuatro análisis, en orden de lo que aportan a una decisión:

1. `diagnostico`  distingue déficits sistémicos de factores diferenciadores
2. `territorial`  agrega por manzana, que es la unidad de gestión real
3. `criticos`     nombra los inmuebles de mayor riesgo y por qué lo son
4. `cruce`        cruza dos amenazas sobre los mismos inmuebles
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


def _indice_total(contribuciones):
    """Índice de riesgo por inmueble a partir de los aportes ponderados."""
    return contribuciones.groupby('id_inmueble')['contribucion'].sum()


def diagnostico(contribuciones, umbral_correlacion=0.40):
    """Separa déficits sistémicos de factores diferenciadores.

    Para cada sub-indicador calcula:

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
    if contribuciones.empty:
        return pd.DataFrame(columns=[
            'subindicador_id', 'subindicador_nombre', 'indicador_nombre',
            'valor_medio', 'aporte_medio', 'aporte_pct', 'correlacion',
            'pct_alto', 'sin_variacion', 'clasificacion',
        ])

    total = _indice_total(contribuciones)
    indice_medio = total.mean()

    aporte = contribuciones.pivot_table(
        index='id_inmueble', columns='subindicador_id', values='contribucion', aggfunc='sum')
    valor = contribuciones.pivot_table(
        index='id_inmueble', columns='subindicador_id', values='valor', aggfunc='mean')

    nombres = (contribuciones
               .drop_duplicates('subindicador_id')
               .set_index('subindicador_id')[['subindicador_nombre', 'indicador_nombre',
                                              'peso_sub', 'peso_ind']])

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
            'subindicador_id': int(sub_id),
            'subindicador_nombre': meta['subindicador_nombre'],
            'indicador_nombre': meta['indicador_nombre'],
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


def territorial(indice, meta):
    """Agrega el índice por manzana.

    53 manzanas de una docena de predios son una unidad de gestión accionable;
    369 predios sueltos no lo son.
    """
    df = indice.merge(meta[['id_inmueble', 'manzana']], on='id_inmueble', how='left')
    df = df[df['manzana'].notna()]
    if df.empty:
        return pd.DataFrame(columns=['manzana', 'n_evaluados', 'indice_medio',
                                     'indice_max', 'n_alto_mas', 'pct_alto_mas'])

    df['nivel'] = df['indice_de_riesgo'].map(niveles.nivel_por_indice)
    es_alto = df['nivel'].isin([niveles.NIVEL_ALTO, niveles.NIVEL_MUY_ALTO])

    agrupado = df.groupby('manzana').agg(
        n_evaluados=('id_inmueble', 'count'),
        indice_medio=('indice_de_riesgo', 'mean'),
        indice_max=('indice_de_riesgo', 'max'),
    )
    agrupado['n_alto_mas'] = es_alto.groupby(df['manzana']).sum()
    agrupado['pct_alto_mas'] = agrupado['n_alto_mas'] / agrupado['n_evaluados'] * 100
    agrupado['nivel_medio'] = agrupado['indice_medio'].map(niveles.nivel_por_indice)

    return (agrupado
            .reset_index()
            .sort_values(['pct_alto_mas', 'indice_medio'], ascending=False)
            .reset_index(drop=True))


def criticos(contribuciones, meta, etiquetas, top=25, n_factores=3):
    """Inmuebles de mayor riesgo, con los factores que más los penalizan.

    Es la sección que convierte el informe en algo accionable: hoy el documento
    no nombra ni un solo inmueble.

    `etiquetas` mapea (subindicador_id, valor) al nombre de la clase, de modo que
    el factor se lee "Materialidad estructural — Entramado de madera" y no
    "Materialidad estructural — 4".
    """
    if contribuciones.empty:
        return pd.DataFrame(columns=['id_inmueble', 'direccion', 'rol_sii', 'manzana',
                                     'indice_de_riesgo', 'nivel', 'factores'])

    total = _indice_total(contribuciones).sort_values(ascending=False)
    elegidos = total.head(top)

    aportes = contribuciones[contribuciones['id_inmueble'].isin(elegidos.index)]
    aportes = aportes.sort_values(['id_inmueble', 'contribucion'], ascending=[True, False])

    def describir(fila):
        clase = (etiquetas.get(int(fila['subindicador_id'])) or {}).get(int(fila['valor']))
        return f"{fila['subindicador_nombre']} — {clase}" if clase else fila['subindicador_nombre']

    factores = (aportes
                .groupby('id_inmueble')
                .head(n_factores)
                .assign(descripcion=lambda d: d.apply(describir, axis=1))
                .groupby('id_inmueble')['descripcion']
                .apply(lambda s: ' · '.join(s)))

    df = pd.DataFrame({'id_inmueble': elegidos.index, 'indice_de_riesgo': elegidos.values})
    df = df.merge(meta[['id_inmueble', 'direccion', 'rol_sii', 'manzana']],
                  on='id_inmueble', how='left')
    df['factores'] = df['id_inmueble'].map(factores)
    df['nivel'] = df['indice_de_riesgo'].map(niveles.nivel_por_indice)
    return df.reset_index(drop=True)


def cruce(indice_a, indice_b, meta, nombre_a='A', nombre_b='B'):
    """Cruza dos amenazas sobre los mismos inmuebles.

    Devuelve un DataFrame por inmueble con ambos índices y sus niveles. Los
    inmuebles evaluados en una sola amenaza se conservan (con NaN en la otra):
    "351 de 369 evaluados en ambas" es en sí mismo un dato del informe.

    En `attrs` deja la correlación de Pearson, el conteo de altos en ambas y la
    matriz de contingencia entre niveles.
    """
    a = indice_a.rename(columns={'indice_de_riesgo': 'indice_a'})
    b = indice_b.rename(columns={'indice_de_riesgo': 'indice_b'})
    df = meta[['id_inmueble', 'direccion', 'rol_sii', 'manzana']].merge(a, on='id_inmueble', how='left')
    df = df.merge(b, on='id_inmueble', how='left')
    df = df[df['indice_a'].notna() | df['indice_b'].notna()].copy()

    df['nivel_a'] = df['indice_a'].map(niveles.nivel_por_indice)
    df['nivel_b'] = df['indice_b'].map(niveles.nivel_por_indice)

    ambas = df[df['indice_a'].notna() & df['indice_b'].notna()]
    altos = (niveles.NIVEL_ALTO, niveles.NIVEL_MUY_ALTO)
    en_ambas = ambas[ambas['nivel_a'].isin(altos) & ambas['nivel_b'].isin(altos)]

    orden = list(niveles.NIVELES_RIESGO)
    matriz = pd.crosstab(
        pd.Categorical(ambas['nivel_b'], categories=orden, ordered=True),
        pd.Categorical(ambas['nivel_a'], categories=orden, ordered=True),
        dropna=False,
    )

    df.attrs.update({
        'nombre_a': nombre_a,
        'nombre_b': nombre_b,
        'n_ambas': int(len(ambas)),
        'n_solo_a': int((df['indice_a'].notna() & df['indice_b'].isna()).sum()),
        'n_solo_b': int((df['indice_b'].notna() & df['indice_a'].isna()).sum()),
        'correlacion': float(ambas['indice_a'].corr(ambas['indice_b'])) if len(ambas) > 1 else float('nan'),
        'n_altos_en_ambas': int(len(en_ambas)),
        'matriz': matriz,
    })

    df['suma'] = df[['indice_a', 'indice_b']].sum(axis=1, min_count=1)
    return df.sort_values('suma', ascending=False).reset_index(drop=True)


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
