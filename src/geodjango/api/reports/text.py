"""Plantillas de texto narrativo del reporte.

La parte cualitativa es fija (plantilla) y los números se inyectan desde los
conteos calculados en la BD. Los textos definitivos son editables aquí.
Devuelven cadenas con marcado básico de ReportLab (<b>, <br/>).
"""

from . import niveles


def _fila(filas, nivel):
    for f in filas:
        if f["nivel"] == nivel:
            return f
    return {"cantidad": 0, "porcentaje": 0}


def intro_resultados_globales(nombres_amenazas):
    amenazas = ", ".join(f"'{n.lower()}'" for n in nombres_amenazas)
    n = len(nombres_amenazas)
    palabra = "amenaza" if n == 1 else "amenazas"
    return (
        f"Los resultados globales para la evaluación de riesgo de desastre frente a "
        f"{'la' if n == 1 else 'las'} {palabra} crítica{'s' if n != 1 else ''} abordada"
        f"{'s' if n != 1 else ''} – {amenazas} – se sintetizan en la <b>Tabla 1</b>."
    )


def parrafo_evaluados(total, no_evaluado):
    evaluados = total - no_evaluado
    return (
        f"Se evaluó un total de <b>{evaluados}</b> inmuebles, quedando <b>{no_evaluado}</b> "
        f"predios sin evaluar por tratarse de espacios públicos o sitios eriazos. "
        f"Como se explicó en informes anteriores, para la estimación del índice de riesgo se "
        f"definieron cuatro rangos, detallados en la <b>Tabla 2</b>."
    )


def parrafo_promedios(promedios):
    """`promedios`: lista de {nombre, promedio, nivel} ordenada desc."""
    partes = []
    for p in promedios:
        partes.append(
            f"'{p['nombre'].lower()}', con un índice promedio "
            f"{p['nivel'].lower()} de {p['promedio']:.2f}".replace(".", ",")
        )
    cuerpo = "; seguido de ".join(partes) if len(partes) > 1 else (partes[0] if partes else "")
    return (
        "Las amenazas que promedian un índice de riesgo más elevado son, en primer lugar, "
        f"{cuerpo}. La incidencia de los diferentes aspectos considerados en la evaluación de "
        "cada amenaza se comenta a continuación, junto con la espacialización de los resultados."
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
    b = _fila(filas, niveles.NIVEL_BAJO)
    m = _fila(filas, niveles.NIVEL_MEDIO)
    a = _fila(filas, niveles.NIVEL_ALTO)
    ma = _fila(filas, niveles.NIVEL_MUY_ALTO)
    ne = _fila(filas, niveles.NIVEL_NO_EVALUADO)
    return (
        f"De los {total} inmuebles, {a['cantidad']} ({a['porcentaje']}%) presentan un índice de "
        f"riesgo alto, {m['cantidad']} ({m['porcentaje']}%) medio, {ma['cantidad']} "
        f"({ma['porcentaje']}%) muy alto y {b['cantidad']} ({b['porcentaje']}%) bajo. "
        f"Y {ne['cantidad']} inmuebles ({ne['porcentaje']}%) no se evaluaron por corresponder a "
        f"sitios eriazos o espacios públicos con rol asignado sin edificaciones. "
        f"Los resultados generales se sintetizan en la <b>Figura 1</b>."
    )


def parrafo_indicadores_primarios():
    return (
        "En cuanto a los resultados obtenidos para los indicadores primarios (<b>Figura 2</b>), "
        "se observa la incidencia de cada uno en el resultado final, según el porcentaje de "
        "inmuebles con valores alto y muy alto que concentra cada indicador."
    )


def parrafo_indicadores_secundarios():
    return (
        "A continuación se detalla la incidencia de cada indicador secundario en los resultados. "
        "Para cada uno se presenta su espacialización, la distribución de inmuebles por nivel y "
        "el promedio obtenido."
    )


def parrafo_subindicador(nombre, promedio, nivel):
    prom = f"{promedio:.2f}".replace(".", ",")
    return (
        f"El indicador secundario '<b>{nombre.lower()}</b>' presenta un resultado "
        f"<b>{nivel.lower()}</b> ({prom})."
    )


def conclusiones(filas, total):
    a = _fila(filas, niveles.NIVEL_ALTO)
    ma = _fila(filas, niveles.NIVEL_MUY_ALTO)
    suma = a["porcentaje"] + ma["porcentaje"]
    return (
        f"Los resultados dan cuenta de un alto índice de vulnerabilidad frente a la amenaza "
        f"incendio, con un {a['porcentaje']}% de los inmuebles con un índice alto y un "
        f"{ma['porcentaje']}% muy alto, que sumados representan el {suma}% del Sitio. "
        f"Existen determinados indicadores que contrastan entre los barrios, cuyo análisis "
        f"permite focalizar estrategias de mitigación. De forma generalizada es prácticamente "
        f"inexistente la gestión del fuego: no existe un plan de gestión de incendios, ni "
        f"inspecciones o actividades de capacitación sistemáticas. De forma transversal se "
        f"observan inmuebles deshabitados, en mal estado de conservación o ruinosos y sitios "
        f"eriazos que actúan como nodos críticos, aumentando el riesgo de los inmuebles aledaños."
    )
