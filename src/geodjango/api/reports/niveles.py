"""Cortes y colores por nivel de riesgo.

Fuente única de verdad en el backend. Debe mantenerse idéntico a
`src/risk-map/src/utils/colores.ts` para que el PDF y la app coincidan:

    riesgo >= 3.26 -> Muy Alto (#ff0000)
    riesgo >= 2.51 -> Alto     (#ff6600)
    riesgo >= 1.76 -> Medio    (#ffff00)
    resto          -> Bajo     (#00aa00)
"""

from collections import Counter

NIVEL_BAJO = "Bajo"
NIVEL_MEDIO = "Medio"
NIVEL_ALTO = "Alto"
NIVEL_MUY_ALTO = "Muy Alto"
NIVEL_NO_EVALUADO = "No evaluado"

# Niveles de riesgo en orden canónico (para tablas, donas y leyendas).
NIVELES_RIESGO = [NIVEL_BAJO, NIVEL_MEDIO, NIVEL_ALTO, NIVEL_MUY_ALTO]
NIVELES = NIVELES_RIESGO + [NIVEL_NO_EVALUADO]

COLORES = {
    NIVEL_BAJO: "#00aa00",
    NIVEL_MEDIO: "#ffff00",
    NIVEL_ALTO: "#ff6600",
    NIVEL_MUY_ALTO: "#ff0000",
    NIVEL_NO_EVALUADO: "#9e9e9e",
}

# Valor crudo de Evaluacion.valor (escala 1..4) -> nivel.
_VALOR_CRUDO = {1: NIVEL_BAJO, 2: NIVEL_MEDIO, 3: NIVEL_ALTO, 4: NIVEL_MUY_ALTO}


def color(nivel):
    """Color hex del nivel."""
    return COLORES.get(nivel, COLORES[NIVEL_NO_EVALUADO])


def nivel_por_indice(valor):
    """Clasifica un índice de riesgo continuo (~1..4) en un nivel.

    Usa los mismos cortes que el frontend. `None`/NaN -> No evaluado.
    """
    if valor is None:
        return NIVEL_NO_EVALUADO
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return NIVEL_NO_EVALUADO
    if v != v:  # NaN
        return NIVEL_NO_EVALUADO
    if v >= 3.26:
        return NIVEL_MUY_ALTO
    if v >= 2.51:
        return NIVEL_ALTO
    if v >= 1.76:
        return NIVEL_MEDIO
    return NIVEL_BAJO


def nivel_por_valor_crudo(valor):
    """Clasifica un valor crudo de evaluación (1..4) en un nivel."""
    try:
        return _VALOR_CRUDO.get(int(valor), NIVEL_NO_EVALUADO)
    except (TypeError, ValueError):
        return NIVEL_NO_EVALUADO


def conteo(niveles_evaluados, total):
    """Construye las filas de conteo por nivel.

    `niveles_evaluados`: iterable con el nivel de cada inmueble EVALUADO
    (sin incluir los no evaluados). `total`: total de inmuebles del sitio.
    "No evaluado" = total - evaluados.

    Devuelve una lista ordenada de dicts: {nivel, cantidad, porcentaje}.
    """
    c = Counter(niveles_evaluados)
    evaluados = sum(c.values())
    c[NIVEL_NO_EVALUADO] = max(total - evaluados, 0)
    filas = []
    for nivel in NIVELES:
        cant = int(c.get(nivel, 0))
        pct = round(cant / total * 100) if total else 0
        filas.append({"nivel": nivel, "cantidad": cant, "porcentaje": pct})
    return filas


def dominante(filas):
    """Nivel de riesgo dominante (mayor cantidad), excluyendo No evaluado."""
    candidatos = [f for f in filas if f["nivel"] in NIVELES_RIESGO]
    if not candidatos:
        return None
    return max(candidatos, key=lambda f: f["cantidad"])["nivel"]
