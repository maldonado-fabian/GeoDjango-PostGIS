"""Adaptador de `api.riesgo` para el informe PDF.

La definición canónica de los niveles vive en `api/riesgo.py`, que además usa
`api/views.py`. Este módulo la expone con la API basada en strings que ya
consumen `pdf.py`, `charts.py` y `text.py`, para no tener que reescribirlos en
el mismo paso en que se consolidaron los umbrales.

Al migrar esos módulos al tipo `Nivel` de `api.riesgo`, este adaptador se borra.
"""

from api import riesgo


# ── Nombres de nivel (la API vieja los trata como strings) ────────────────────

NIVEL_BAJO = riesgo.BAJO.label
NIVEL_MEDIO = riesgo.MEDIO.label
NIVEL_ALTO = riesgo.ALTO.label
NIVEL_MUY_ALTO = riesgo.MUY_ALTO.label
NIVEL_NO_EVALUADO = riesgo.NO_EVALUADO.label

#: Niveles de riesgo en orden ascendente, sin "No evaluado".
NIVELES_RIESGO = [n.label for n in riesgo.NIVELES_ASC]

#: Todos los niveles, incluido "No evaluado" (para tablas, donas y leyendas).
NIVELES = [n.label for n in riesgo.TODOS]

COLORES = {n.label: n.color for n in riesgo.TODOS}

#: Versión oscura legible sobre blanco. El relleno nunca debe usarse como texto.
COLORES_TEXTO = {n.label: n.color_texto for n in riesgo.TODOS}


def color(nivel):
    """Color de relleno del nivel."""
    return COLORES.get(nivel, COLORES[NIVEL_NO_EVALUADO])


def color_texto(nivel):
    """Color legible sobre fondo blanco para cifras y etiquetas."""
    return COLORES_TEXTO.get(nivel, COLORES_TEXTO[NIVEL_NO_EVALUADO])


def rango_texto(nivel):
    """'2,51 – 3,25', derivado de los cortes canónicos."""
    return riesgo.rango_texto(riesgo.por_label(nivel))


def nivel_por_indice(valor):
    """Clasifica un índice continuo (1–4). Devuelve el nombre del nivel."""
    return riesgo.nivel_por_indice(valor).label


def nivel_por_valor_crudo(valor):
    """Clasifica un valor crudo de evaluación (1..4). Devuelve el nombre."""
    return riesgo.nivel_por_valor_crudo(valor).label


def conteo(niveles_evaluados, total):
    """Filas {nivel, cantidad, porcentaje} por nivel, con los no evaluados imputados."""
    filas = riesgo.conteo(
        (riesgo.por_label(n) for n in niveles_evaluados),
        total,
    )
    return [
        {'nivel': f['nivel'].label, 'cantidad': f['cantidad'], 'porcentaje': f['porcentaje']}
        for f in filas
    ]


def dominante(filas):
    """Nivel con más inmuebles, excluyendo "No evaluado". `None` si no hay datos."""
    nivel = riesgo.dominante(
        [{'nivel': riesgo.por_label(f['nivel']), 'cantidad': f['cantidad']} for f in filas]
    )
    return nivel.label if nivel else None
