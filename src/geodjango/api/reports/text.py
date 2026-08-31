"""Plantillas de texto narrativo del informe.

La parte cualitativa es plantilla y los números se inyectan desde los conteos
calculados en la base. Devuelven cadenas con marcado básico de ReportLab
(<b>, <br/>).

Regla que este módulo debe respetar: **ninguna afirmación específica de una
amenaza puede quedar escrita en una plantilla genérica**. Antes las conclusiones
hablaban de "la gestión del fuego" y de "un plan de gestión de incendios" en
cualquier informe, de modo que el de Sismo afirmaba cosas falsas. Lo que sea
propio de una amenaza va en `NOTAS_POR_AMENAZA`, indexado por nombre.
"""

from . import niveles


def _fila(filas, nivel):
    for f in filas:
        if f["nivel"] == nivel:
            return f
    return {"cantidad": 0, "porcentaje": 0}


def _num(valor, decimales=2):
    """2.73 -> '2,73'. Sólo sobre el número, nunca sobre la frase entera."""
    return f"{valor:.{decimales}f}".replace(".", ",")


# ── Descriptores de nivel (Tabla 2) ──────────────────────────────────────────
# Contenido editorial, indexado por nivel. Vive aquí y no en `api/riesgo.py`
# para que ese módulo, que importa `views.py`, no cargue con prosa del informe.

DESCRIPTORES_NIVEL = {
    niveles.NIVEL_BAJO:
        "Los riesgos son aceptables. Se deben implementar medidas para reducir aún más el "
        "riesgo junto con otras mejoras de seguridad.",
    niveles.NIVEL_MEDIO:
        "El riesgo puede ser aceptable a corto plazo. Los planes para reducir y mitigar los "
        "riesgos deben incluirse en los planes futuros.",
    niveles.NIVEL_ALTO:
        "El riesgo es inaceptable. Las medidas para reducir y mitigar el riesgo se deben "
        "implementar lo antes posible.",
    niveles.NIVEL_MUY_ALTO:
        "El riesgo es inaceptable. Se deben tomar medidas inmediatas para mitigar y reducir "
        "estos riesgos.",
}


# ── Notas específicas por amenaza ────────────────────────────────────────────
# Observaciones cualitativas del equipo evaluador que sólo aplican a una amenaza.
# Si una amenaza no está aquí, sus conclusiones se limitan a lo que dicen los
# números, que es preferible a afirmar algo que no se midió.

NOTAS_POR_AMENAZA = {
    "Incendio":
        "De forma generalizada es prácticamente inexistente la gestión del fuego: no existe "
        "un plan de gestión de incendios, ni inspecciones o actividades de capacitación "
        "sistemáticas. De forma transversal se observan inmuebles deshabitados, en mal estado "
        "de conservación o ruinosos y sitios eriazos que actúan como nodos críticos, "
        "aumentando el riesgo de los inmuebles aledaños.",
}


def intro_resultados_globales(nombres_amenazas):
    amenazas = ", ".join(f"'{n.lower()}'" for n in nombres_amenazas)
    n = len(nombres_amenazas)
    palabra = "amenaza" if n == 1 else "amenazas"
    return (
        f"Los resultados globales para la evaluación de riesgo de desastre frente a "
        f"{'la' if n == 1 else 'las'} {palabra} crítica{'s' if n != 1 else ''} abordada"
        f"{'s' if n != 1 else ''} – {amenazas} – se sintetizan en la <b>Tabla 1</b>."
    )


def parrafo_evaluados(total, no_evaluado, nombre_amenaza):
    evaluados = total - no_evaluado
    return (
        f"Para la amenaza {nombre_amenaza.lower()} se evaluó un total de <b>{evaluados}</b> "
        f"inmuebles, quedando <b>{no_evaluado}</b> predios sin evaluar por tratarse de espacios "
        f"públicos o sitios eriazos. Para la estimación del índice de riesgo se definieron "
        f"cuatro rangos, detallados en la <b>Tabla 2</b>."
    )


def parrafo_promedios(promedios):
    """`promedios`: lista de {nombre, promedio, nivel} ordenada desc."""
    if not promedios:
        return ""

    if len(promedios) == 1:
        p = promedios[0]
        cuerpo = (
            f"La amenaza evaluada, '{p['nombre'].lower()}', promedia un índice de riesgo "
            f"{p['nivel'].lower()} de {_num(p['promedio'])}."
        )
    else:
        partes = [
            f"'{p['nombre'].lower()}', con un índice promedio {p['nivel'].lower()} "
            f"de {_num(p['promedio'])}"
            for p in promedios
        ]
        cuerpo = (
            "Las amenazas que promedian un índice de riesgo más elevado son, en primer lugar, "
            + "; seguida de ".join(partes) + "."
        )

    return (
        cuerpo
        + " La incidencia de los diferentes aspectos considerados en la evaluación de cada "
          "amenaza se comenta a continuación, junto con la espacialización de los resultados."
    )


def detalle_amenaza_intro(nombre, nombres_indicadores):
    aspectos = ", ".join(f"'{n.lower()}'" for n in nombres_indicadores)
    return (
        f"Para la amenaza {nombre.lower()} la evaluación consideró los siguientes aspectos: "
        f"{aspectos}. No se evaluaron los predios identificados como eriazos, entendidos como "
        f"los sitios donde no quedan vestigios físicos a conservar en una futura restauración "
        f"y/o habilitación."
    )


def _listado_por_magnitud(filas, niveles_incluidos):
    """'X (Y%) alto, Z (W%) medio y N (M%) bajo' — en orden de magnitud, no fijo.

    Antes el orden era literal (alto, medio, muy alto, bajo), así que cuando
    dominaba el nivel bajo la frase abría igual por el alto y se leía torcido.
    """
    evaluados = [_fila(filas, n) | {"nivel": n} for n in niveles_incluidos]
    evaluados.sort(key=lambda f: f["cantidad"], reverse=True)
    partes = [
        f"{f['cantidad']} ({f['porcentaje']}%) {f['nivel'].lower()}"
        for f in evaluados if f["cantidad"] > 0
    ]
    if not partes:
        return ""
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]


def parrafo_resultados_amenaza(filas, total):
    """Describe la distribución en orden de magnitud."""
    ne = _fila(filas, niveles.NIVEL_NO_EVALUADO)
    listado = _listado_por_magnitud(filas, niveles.NIVELES_RIESGO)
    if not listado:
        return f"De los {total} inmuebles del sitio, ninguno cuenta con evaluación registrada."

    return (
        f"De los {total} inmuebles del sitio, presentan un índice de riesgo {listado}. "
        f"Otros {ne['cantidad']} ({ne['porcentaje']}%) no se evaluaron por corresponder a sitios "
        f"eriazos o espacios públicos con rol asignado sin edificaciones. Los resultados "
        f"generales se sintetizan en la <b>Figura 1</b>."
    )


def parrafo_indicadores_primarios():
    return (
        "Cada indicador primario se presenta con su espacialización, la distribución de "
        "inmuebles por nivel y su promedio. Ver dónde se concentra cada indicador, y no sólo "
        "cuánto suma, es lo que permite decidir en qué parte del sitio actuar sobre él."
    )


def parrafo_indicadores_secundarios():
    return (
        "El mismo detalle, al nivel de indicador secundario: es la granularidad a la que se "
        "define la obra concreta sobre cada inmueble."
    )


def parrafo_subindicador(nombre, promedio, nivel):
    return (
        f"El indicador secundario '<b>{nombre.lower()}</b>' presenta un resultado "
        f"<b>{nivel.lower()}</b> ({_num(promedio)})."
    )


def _parrafo_detalle_factor(etiqueta, nombre, descripcion, filas, promedio):
    """Párrafo común a indicadores y sub-indicadores: descripción oficial (si
    existe) + distribución real por nivel + promedio. Ambos niveles evalúan en
    escala 1 a 4, así que el promedio siempre se expresa "sobre 4".
    """
    nivel_prom = niveles.nivel_por_indice(promedio)
    listado = _listado_por_magnitud(filas, niveles.NIVELES_RIESGO)

    frase_descripcion = f" {descripcion}." if descripcion else ""
    frase_distribucion = (
        f" Del total de inmuebles evaluados para este {etiqueta}, {listado}."
        if listado else
        f" No se registran inmuebles evaluados para este {etiqueta}."
    )

    return (
        f"<b>{nombre}.</b>{frase_descripcion}{frase_distribucion} El promedio alcanzado es de "
        f"{_num(promedio)} sobre 4, lo que corresponde a un nivel <b>{nivel_prom.lower()}</b>."
    )


def parrafo_indicador_detalle(nombre, descripcion, filas, promedio):
    return _parrafo_detalle_factor('indicador', nombre, descripcion, filas, promedio)


def parrafo_subindicador_detalle(nombre, descripcion, filas, promedio):
    return _parrafo_detalle_factor('indicador secundario', nombre, descripcion, filas, promedio)


def parrafo_distribucion(dist, nombre_amenaza):
    return (
        f"El índice de riesgo frente a {nombre_amenaza.lower()} se distribuye entre "
        f"{_num(dist['min'])} y {_num(dist['max'])}, con una mediana de {_num(dist['mediana'])} y "
        f"una desviación estándar de {_num(dist['desv'])}. La mitad central de los inmuebles se "
        f"ubica entre {_num(dist['q1'])} y {_num(dist['q3'])}."
    )


# ── Qué factores explican el riesgo ──────────────────────────────────────────

def intro_rangos():
    return (
        "La <b>Tabla 2</b> detalla el significado de cada rango del índice y el criterio de "
        "acción que corresponde a cada uno, según la magnitud del riesgo involucrado."
    )


def intro_factores(top_nombre, top_pct):
    return (
        "El gráfico y la tabla siguientes muestran cuánto aporta cada indicador primario al "
        f"índice de riesgo: entre más ancha la barra, más pesa ese factor en el resultado "
        f"final. '<b>{top_nombre}</b>' es el que más incide, con el {_num(top_pct, 1)}% del "
        "índice total."
    )


# ── Puntos críticos y recomendaciones ────────────────────────────────────────
# Todo lo que sigue se deriva estrictamente del ranking de aporte por factor
# (`analytics.aporte_por_factor`): ninguna frase afirma algo que los datos no
# midan directamente. Mismo criterio que ya rige `NOTAS_POR_AMENAZA`.

def intro_puntos_criticos(nombre_amenaza):
    return (
        f"Esta sección identifica, a partir del aporte de cada indicador al índice, los "
        f"aspectos que más inciden en el resultado de la evaluación frente a la amenaza "
        f"{nombre_amenaza.lower()} y en qué temas conviene concentrar la atención."
    )


def parrafo_puntos_criticos(top_indicadores, top_subindicadores):
    """`top_indicadores`/`top_subindicadores`: DataFrames de `aporte_por_factor`,
    ya ordenados de mayor a menor aporte."""
    if top_indicadores.empty or top_subindicadores.empty:
        return "No hay suficientes evaluaciones registradas para identificar puntos críticos."

    ind = top_indicadores.iloc[0]
    subs = top_subindicadores.head(3)
    nombres_sub = ", ".join(f"'{n}'" for n in subs['factor_nombre'])

    return (
        f"A nivel de indicador primario, '<b>{ind['factor_nombre']}</b>' concentra el mayor "
        f"aporte al índice ({_num(ind['aporte_pct'], 1)}%), con un promedio de "
        f"{_num(ind['valor_medio'])} sobre 4. A nivel de indicador secundario, los que más "
        f"aportan son {nombres_sub}, que en conjunto explican el "
        f"{_num(subs['aporte_pct'].sum(), 1)}% del índice de riesgo. La Figura y la Tabla "
        f"siguientes detallan los {len(top_subindicadores.head(8))} indicadores secundarios "
        f"de mayor aporte."
    )


def recomendaciones(top_subindicadores, dist, total_inmuebles):
    """Frases de recomendación derivadas del ranking de aporte, sin agregar
    ninguna afirmación que los datos no sustenten directamente."""
    salida = []

    for _, fila in top_subindicadores.head(3).iterrows():
        salida.append(
            f"Priorizar la atención sobre «{fila['factor_nombre']}», que concentra el "
            f"{_num(fila['aporte_pct'], 1)}% del índice de riesgo con un promedio de "
            f"{_num(fila['valor_medio'])} sobre 4 en los inmuebles evaluados."
        )

    if len(top_subindicadores) > 3:
        resto = top_subindicadores.iloc[3:8]
        nombres = ", ".join(f"«{n}»" for n in resto['factor_nombre'])
        if nombres:
            salida.append(
                f"Mantener en observación los indicadores secundarios {nombres}, que también "
                f"figuran entre los de mayor aporte al índice."
            )

    if dist and dist['n'] < total_inmuebles:
        pendientes = total_inmuebles - dist['n']
        salida.append(
            f"Completar la evaluación de los {pendientes} predios del catastro que aún no "
            f"cuentan con evaluación registrada, para que el índice represente la totalidad "
            f"del sitio."
        )

    return salida


# ── Conclusiones ─────────────────────────────────────────────────────────────

def conclusiones(filas, nombre_amenaza):
    """Conclusiones de la amenaza evaluada.

    El veredicto se deriva de los datos: antes la frase afirmaba "un alto índice
    de vulnerabilidad" pasara lo que pasara, incluso si dominaba el nivel bajo.
    """
    alto = _fila(filas, niveles.NIVEL_ALTO)
    muy_alto = _fila(filas, niveles.NIVEL_MUY_ALTO)
    suma = alto["porcentaje"] + muy_alto["porcentaje"]

    if suma >= 50:
        veredicto = "un alto índice de vulnerabilidad"
    elif suma >= 25:
        veredicto = "una vulnerabilidad significativa"
    else:
        veredicto = "una vulnerabilidad acotada"

    parrafo = (
        f"Los resultados dan cuenta de {veredicto} frente a la amenaza "
        f"{nombre_amenaza.lower()}, con un {alto['porcentaje']}% de los inmuebles en índice alto "
        f"y un {muy_alto['porcentaje']}% muy alto, que sumados representan el {suma}% del Sitio. "
        f"Existen determinados indicadores que contrastan entre los barrios, cuyo análisis "
        f"permite focalizar estrategias de mitigación."
    )

    nota = NOTAS_POR_AMENAZA.get(nombre_amenaza)
    return f"{parrafo} {nota}" if nota else parrafo
