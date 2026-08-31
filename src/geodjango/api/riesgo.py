"""Definición canónica del índice de riesgo y sus niveles.

Fuente única de verdad para toda la plataforma. Antes de este módulo los cortes
vivían en tres lugares que no coincidían:

- `api/reports/niveles.py`  cortes por cota inferior  (>= 1.76 / 2.51 / 3.26)
- `api/views.py`            cortes por cota superior  (<= 1.75 / 2.5 / 3.25)
                            y además con otra paleta (#00FF00/#FFA500...)
- `src/mapa/main.js`        coincidía con niveles.py

Los huecos de 0,01 hacían que un índice de 2,505 fuera "Medio" en el PDF y
"Alto" en el KML del mismo dato. Ver `api/tests/test_umbrales.py`.

Este módulo NO importa matplotlib, pandas ni nada pesado: `views.py` lo importa
en el proceso web, donde `api/reports/` no debe entrar.

El frontend replica estos cortes en `src/mapa/main.js` porque no puede importar
Python; la paridad se verifica por test, no en runtime.
"""

from dataclasses import dataclass
from math import isnan


# ── Escala ────────────────────────────────────────────────────────────────────

# El índice es una suma ponderada de valores 1..4 con pesos que suman 1 por
# nivel, así que queda acotado a [1, 4].
ESCALA_MIN = 1.0
ESCALA_MAX = 4.0

# Resolución de la escala: los rangos se expresan con dos decimales, de modo que
# el techo de un nivel es el piso del siguiente menos este paso.
PASO = 0.01


@dataclass(frozen=True)
class Nivel:
    """Un nivel de riesgo.

    `color` es el relleno (mapas, barras, swatches). `color_texto` es la versión
    oscura legible sobre fondo blanco: el amarillo puro sobre blanco da ~1,07:1
    de contraste y nunca debe usarse como color de texto.
    """

    key: str
    label: str
    minimo: float
    color: str
    color_texto: str

    def __str__(self):
        return self.label


MUY_ALTO = Nivel('muyalto', 'Muy Alto', 3.26, '#ff0000', '#c20000')
ALTO     = Nivel('alto',    'Alto',     2.51, '#ff6600', '#a33f00')
MEDIO    = Nivel('medio',   'Medio',    1.76, '#ffff00', '#75690a')
BAJO     = Nivel('bajo',    'Bajo',     ESCALA_MIN, '#00aa00', '#00752b')

NO_EVALUADO = Nivel('noeval', 'No evaluado', float('nan'), '#9e9e9e', '#5b5f60')

#: Niveles de riesgo en orden descendente. El orden importa: `nivel_por_indice`
#: devuelve el primero cuyo mínimo se alcanza.
NIVELES = (MUY_ALTO, ALTO, MEDIO, BAJO)

#: Orden canónico ascendente para tablas, leyendas y donas.
NIVELES_ASC = (BAJO, MEDIO, ALTO, MUY_ALTO)

#: Incluye "No evaluado", que en tablas es una fila más pero no un nivel de riesgo.
TODOS = NIVELES_ASC + (NO_EVALUADO,)

_POR_KEY = {n.key: n for n in TODOS}
_POR_LABEL = {n.label: n for n in TODOS}

#: Valor crudo de una evaluación (1..4) -> nivel.
_VALOR_CRUDO = {1: BAJO, 2: MEDIO, 3: ALTO, 4: MUY_ALTO}


# ── Clasificación ─────────────────────────────────────────────────────────────

def nivel_por_indice(valor):
    """Clasifica un índice de riesgo continuo (escala 1–4) en un `Nivel`.

    `None`, NaN o cualquier cosa no numérica devuelve `NO_EVALUADO`.
    """
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return NO_EVALUADO
    if isnan(v):
        return NO_EVALUADO
    for nivel in NIVELES:
        if v >= nivel.minimo:
            return nivel
    return BAJO


def nivel_por_valor_crudo(valor):
    """Clasifica el valor crudo de una evaluación (1..4) en un `Nivel`.

    Fuera de ese rango -incluido el 0, que es el default de `Evaluacion.valor`-
    devuelve `NO_EVALUADO`.
    """
    try:
        return _VALOR_CRUDO.get(int(valor), NO_EVALUADO)
    except (TypeError, ValueError):
        return NO_EVALUADO


def por_key(key):
    return _POR_KEY[key]


def por_label(label):
    return _POR_LABEL[label]


# ── Presentación ──────────────────────────────────────────────────────────────

def _fmt(valor):
    """2.51 -> '2,51'. Formato numérico chileno."""
    return f'{valor:.2f}'.replace('.', ',')


def techo(nivel):
    """Cota superior del nivel, o `ESCALA_MAX` para el más alto."""
    if nivel is NO_EVALUADO:
        return None
    idx = NIVELES.index(nivel)
    if idx == 0:
        return ESCALA_MAX
    return NIVELES[idx - 1].minimo - PASO


def rango_texto(nivel):
    """'2,51 – 3,25'. Derivado de los cortes, no escrito a mano.

    Antes estos textos estaban duplicados como literales en la Tabla 2 del PDF,
    así que cambiar un corte desincronizaba la tabla en silencio.
    """
    if nivel is NO_EVALUADO:
        return '—'
    return f'{_fmt(nivel.minimo)} – {_fmt(techo(nivel))}'


def rango_texto_corto(nivel):
    """'≥ 3,26' para el nivel más alto, '< 1,76' para el más bajo."""
    if nivel is NO_EVALUADO:
        return '—'
    if nivel is NIVELES[0]:
        return f'≥ {_fmt(nivel.minimo)}'
    if nivel is NIVELES[-1]:
        return f'< {_fmt(NIVELES[-2].minimo)}'
    return rango_texto(nivel)


# ── Agregación ────────────────────────────────────────────────────────────────

def conteo(niveles_evaluados, total):
    """Filas de conteo por nivel a partir de los niveles de los inmuebles evaluados.

    `niveles_evaluados` son los `Nivel` de los inmuebles CON evaluación; el resto
    hasta `total` se imputa a "No evaluado".

    Devuelve una lista de dicts {nivel, cantidad, porcentaje} en orden ascendente
    más la fila de no evaluados. Los porcentajes se redondean por separado, así
    que pueden no sumar exactamente 100.
    """
    conteos = {n.key: 0 for n in TODOS}
    evaluados = 0
    for nivel in niveles_evaluados:
        conteos[nivel.key] = conteos.get(nivel.key, 0) + 1
        evaluados += 1
    conteos[NO_EVALUADO.key] = max(total - evaluados, 0)

    return [
        {
            'nivel': nivel,
            'cantidad': conteos[nivel.key],
            'porcentaje': round(conteos[nivel.key] / total * 100) if total else 0,
        }
        for nivel in TODOS
    ]


def dominante(filas):
    """Nivel con más inmuebles, excluyendo "No evaluado". `None` si no hay datos."""
    candidatos = [f for f in filas if f['nivel'] is not NO_EVALUADO]
    if not candidatos or all(f['cantidad'] == 0 for f in candidatos):
        return None
    return max(candidatos, key=lambda f: f['cantidad'])['nivel']


# ── SQL ───────────────────────────────────────────────────────────────────────

#: Índice de riesgo por inmueble para una amenaza.
#:
#: indice = Σ_indicador [ peso_indicador × Σ_subindicador ( valor × peso_subindicador ) ]
#:
#: Se mantiene en Python y no en `sql/*.sql` a propósito: esos scripts se aplican
#: a mano, y una dependencia no aplicada fallaría dentro del worker de Celery
#: como un genérico "No se pudo generar el PDF".
#:
#: Usa el parámetro ligado `:amenaza_id`. Con SQLAlchemy hay que envolverlo en
#: `sqlalchemy.text()`.
INDICE_SQL = """
    SELECT id_inmueble, SUM(total) AS indice_de_riesgo
    FROM (
        SELECT e.id_inmueble, ind.id AS indicador_id,
               SUM(e.valor * si.peso) * ind.peso AS total
        FROM evaluacion e
        JOIN sub_indicadores si ON e.id_subindicador = si.id
        JOIN indicadores ind ON si.indicador_id = ind.id
        WHERE ind.amenaza_id = :amenaza_id
        GROUP BY e.id_inmueble, ind.id, ind.peso
    ) t
    GROUP BY id_inmueble
"""


def case_sql(expr, campo='color'):
    """`CASE ... END` que clasifica `expr` con los mismos cortes que Python.

    `campo` elige qué devuelve: 'color' (relleno hex), 'color_texto' o 'label'.

    Emitirlo desde la misma tabla de niveles es lo que evita que el SQL y el
    Python se separen, que es exactamente lo que había pasado.
    """
    atributo = {'color': 'color', 'color_texto': 'color_texto', 'label': 'label'}[campo]
    ramas = '\n'.join(
        f"                WHEN {expr} >= {n.minimo} THEN '{getattr(n, atributo)}'"
        for n in NIVELES[:-1]
    )
    return (
        "CASE\n"
        f"{ramas}\n"
        f"                ELSE '{getattr(NIVELES[-1], atributo)}'\n"
        "            END"
    )
