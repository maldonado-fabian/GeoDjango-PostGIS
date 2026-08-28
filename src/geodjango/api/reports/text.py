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


def parrafo_resultados_amenaza(filas, total):
    """Describe la distribución en orden de magnitud, no en un orden fijo.

    Antes el orden era literal (alto, medio, muy alto, bajo), así que cuando
    dominaba el nivel bajo la frase abría igual por el alto y se leía torcido.
    """
    ne = _fila(filas, niveles.NIVEL_NO_EVALUADO)
    evaluados = [
        _fila(filas, n) | {"nivel": n}
        for n in niveles.NIVELES_RIESGO
    ]
    evaluados.sort(key=lambda f: f["cantidad"], reverse=True)

    partes = [
        f"{f['cantidad']} ({f['porcentaje']}%) {f['nivel'].lower()}"
        for f in evaluados if f["cantidad"] > 0
    ]
    if not partes:
        return f"De los {total} inmuebles del sitio, ninguno cuenta con evaluación registrada."

    listado = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]
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


def parrafo_distribucion(dist, nombre_amenaza):
    return (
        f"El índice de riesgo frente a {nombre_amenaza.lower()} se distribuye entre "
        f"{_num(dist['min'])} y {_num(dist['max'])}, con una mediana de {_num(dist['mediana'])} y "
        f"una desviación estándar de {_num(dist['desv'])}. La mitad central de los inmuebles se "
        f"ubica entre {_num(dist['q1'])} y {_num(dist['q3'])}."
    )


# ── Qué factores explican el riesgo ──────────────────────────────────────────

def intro_factores():
    return (
        "El gráfico y la tabla siguientes muestran cuánto aporta cada indicador al índice de "
        "riesgo: entre más ancha la barra, más pesa ese factor en el resultado final."
    )


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
