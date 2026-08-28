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
    return (
        f"El indicador secundario '<b>{nombre.lower()}</b>' presenta un resultado "
        f"<b>{nivel.lower()}</b> ({_num(promedio)})."
    )


# ── Resumen ejecutivo ────────────────────────────────────────────────────────

def intro_resumen_ejecutivo(nombre_amenaza):
    return (
        f"Síntesis de la evaluación de riesgo frente a la amenaza "
        f"{nombre_amenaza.lower()}. Cada hallazgo se acompaña de la decisión que habilita; "
        f"el detalle que lo sustenta está en las secciones siguientes."
    )


def hallazgos(ctx):
    """Hallazgos con su número y la decisión que implican.

    Se derivan de los datos: si el reparto cambia, cambia el texto.
    """
    from .analytics import DIFERENCIADOR, SISTEMICO

    salida = []
    filas = ctx.filas_nivel()
    alto = _fila(filas, niveles.NIVEL_ALTO)
    muy_alto = _fila(filas, niveles.NIVEL_MUY_ALTO)
    dist = ctx.distribucion

    # 1. Magnitud del problema
    if dist:
        salida.append({
            'titulo': f"{alto['cantidad'] + muy_alto['cantidad']} inmuebles en riesgo alto o muy alto",
            'cuerpo': (
                f"De los {dist['n']} inmuebles evaluados, {alto['cantidad']} presentan riesgo alto y "
                f"{muy_alto['cantidad']} muy alto. El índice mediano es {_num(dist['mediana'])} sobre "
                f"{_num(4)}, con una dispersión de {_num(dist['desv'])}: el sitio se comporta de forma "
                f"homogénea, no hay un puñado de casos aislados."
            ),
            'implicancia': (
                'La intervención no puede limitarse a casos puntuales; requiere una estrategia '
                'de escala para el conjunto del sitio.'
            ),
        })

    # 2. Sistémico vs. diferenciador
    diag = ctx.diagnostico
    if not diag.empty:
        sistemicos = diag[diag['clasificacion'] == SISTEMICO]
        diferenciadores = diag[diag['clasificacion'] == DIFERENCIADOR]
        if not sistemicos.empty:
            top = sistemicos.iloc[0]
            salida.append({
                'titulo': f"El mayor aporte al riesgo es una carencia del sitio, no de los predios",
                'cuerpo': (
                    f"'{top['subindicador_nombre']}' explica el {_num(top['aporte_pct'], 1)}% del índice, "
                    f"pero {top['pct_alto']:.0f}% de los inmuebles puntúa en el rango alto y su "
                    f"correlación con el resto del índice es de sólo {_num(top['correlacion'])}: "
                    f"prácticamente todos los inmuebles están igual de mal. "
                    f"Hay {len(sistemicos)} sub-indicadores en esta situación."
                ),
                'implicancia': (
                    'Estos déficits se corrigen con una sola intervención programática para todo '
                    'el sitio, no con obras predio a predio. Es la acción de mayor retorno.'
                ),
            })
        if not diferenciadores.empty:
            nombres = ', '.join(f"'{n}'" for n in diferenciadores['subindicador_nombre'].head(3))
            salida.append({
                'titulo': f"{len(diferenciadores)} factores sí distinguen unos inmuebles de otros",
                'cuerpo': (
                    f"{nombres} concentran a la vez peso en el índice y capacidad de separar "
                    f"inmuebles entre sí. Son los que explican por qué unos predios puntúan más "
                    f"alto que sus vecinos."
                ),
                'implicancia': (
                    'Sobre estos factores la intervención focalizada predio a predio sí cambia el '
                    'resultado, y permite priorizar con criterio.'
                ),
            })

    # 3. Concentración territorial
    terr = ctx.territorial
    if not terr.empty:
        criticas = terr[terr['pct_alto_mas'] >= 100]
        if not criticas.empty:
            inmuebles_afectados = int(criticas['n_evaluados'].sum())
            salida.append({
                'titulo': f"{len(criticas)} manzanas tienen el 100% de sus inmuebles en riesgo alto",
                'cuerpo': (
                    f"Concentran {inmuebles_afectados} inmuebles. La manzana "
                    f"{criticas.iloc[0]['manzana']} encabeza la lista con un índice medio de "
                    f"{_num(criticas.iloc[0]['indice_medio'])}."
                ),
                'implicancia': (
                    'La manzana es una unidad de intervención más eficiente que el predio: '
                    'permite actuar sobre el contagio entre inmuebles contiguos.'
                ),
            })

    # 4. Multi-amenaza
    cruce = ctx.cruce
    if cruce is not None and cruce.attrs['n_altos_en_ambas']:
        r = cruce.attrs['correlacion']
        salida.append({
            'titulo': (
                f"{cruce.attrs['n_altos_en_ambas']} inmuebles acumulan riesgo alto en "
                f"{cruce.attrs['nombre_a'].lower()} y {cruce.attrs['nombre_b'].lower()}"
            ),
            'cuerpo': (
                f"La correlación entre ambos índices es de {_num(r)}: las dos amenazas afectan en "
                f"parte a los mismos inmuebles, pero no son el mismo problema. Reducir una no "
                f"reduce automáticamente la otra."
            ),
            'implicancia': (
                'Estos inmuebles deben encabezar cualquier priorización: una sola intervención '
                'sobre ellos reduce exposición frente a dos amenazas.'
            ),
        })

    # 5. Cobertura del dato
    if dist and dist['n'] < ctx.total_inmuebles:
        sin_evaluar = ctx.total_inmuebles - dist['n']
        salida.append({
            'titulo': f"{sin_evaluar} predios del catastro siguen sin evaluar",
            'cuerpo': (
                f"Se evaluaron {dist['n']} de {ctx.total_inmuebles} inmuebles catastrados. Los "
                f"restantes corresponden a sitios eriazos o espacios públicos con rol asignado "
                f"sin edificaciones."
            ),
            'implicancia': (
                'Los porcentajes de este informe se calculan sobre el total catastrado, de modo '
                'que son conservadores respecto del universo efectivamente edificado.'
            ),
        })

    return salida


def parrafo_distribucion(dist, nombre_amenaza):
    return (
        f"El índice de riesgo frente a {nombre_amenaza.lower()} se distribuye entre "
        f"{_num(dist['min'])} y {_num(dist['max'])}, con una mediana de {_num(dist['mediana'])} y "
        f"una desviación estándar de {_num(dist['desv'])}. La mitad central de los inmuebles se "
        f"ubica entre {_num(dist['q1'])} y {_num(dist['q3'])}."
    )


# ── Metodología ──────────────────────────────────────────────────────────────

def parrafo_metodologia(ctx):
    n_ind = len(ctx.indicadores)
    n_sub = ctx.contribuciones['subindicador_id'].nunique()
    return (
        f"El índice de riesgo de cada inmueble es la suma ponderada de {n_ind} indicadores "
        f"primarios, cada uno compuesto a su vez por sus indicadores secundarios: se multiplica "
        f"el puntaje de cada indicador secundario (escala 1 a 4) por su peso relativo dentro del "
        f"indicador primario, y el resultado por el peso del indicador primario dentro de la "
        f"amenaza. Los pesos de cada nivel suman 1, de modo que el índice queda acotado al mismo "
        f"rango 1 a 4 que los puntajes de origen. La amenaza {ctx.nombre_amenaza.lower()} se "
        f"evalúa con {n_sub} indicadores secundarios."
    )


def parrafo_pesos():
    return (
        "Los pesos los define la unidad técnica y no se derivan de los datos. La columna «peso "
        "efectivo» es el producto de ambos niveles: es cuánto puede aportar como máximo cada "
        "indicador secundario al índice final."
    )


def cobertura_faltante(ctx):
    """Describe los huecos de evaluación en vez de esconderlos en los conteos."""
    esperado = ctx.contribuciones['id_inmueble'].nunique()
    por_sub = ctx.contribuciones.groupby('subindicador_nombre')['id_inmueble'].nunique()
    incompletos = por_sub[por_sub < esperado]

    base = (
        f"Se evaluaron {esperado} inmuebles de los {ctx.total_inmuebles} catastrados. "
        f"Los porcentajes de este informe usan como denominador el total catastrado."
    )
    if incompletos.empty:
        return base + " Todos los indicadores secundarios tienen evaluación completa."

    detalle = '; '.join(
        f"'{nombre}' ({esperado - n} sin evaluar)" for nombre, n in incompletos.items()
    )
    return (
        base + f" Hay indicadores secundarios con evaluación incompleta: {detalle}. "
        f"En esas figuras la diferencia se contabiliza como «no evaluado»."
    )


# ── Diagnóstico ──────────────────────────────────────────────────────────────

def intro_diagnostico():
    return (
        "No todos los factores que elevan el índice se corrigen de la misma manera. Un factor "
        "que pesa mucho pero en el que casi todos los inmuebles puntúan igual señala una "
        "carencia del sitio en su conjunto, y se resuelve con una sola intervención "
        "programática. Un factor que además separa unos inmuebles de otros señala dónde la "
        "intervención predio a predio rinde. Distinguirlos es lo que permite decidir en qué "
        "gastar primero."
    )


def parrafo_diagnostico(df):
    from .analytics import DIFERENCIADOR, SISTEMICO

    sistemicos = df[df['clasificacion'] == SISTEMICO]
    diferenciadores = df[df['clasificacion'] == DIFERENCIADOR]
    if sistemicos.empty and diferenciadores.empty:
        return "Ningún sub-indicador concentra a la vez aporte y capacidad de discriminar."

    partes = []
    if not sistemicos.empty:
        aporte = sistemicos['aporte_pct'].sum()
        partes.append(
            f"{len(sistemicos)} sub-indicadores se comportan como déficits sistémicos y suman "
            f"el {_num(aporte, 1)}% del índice: pesan, pero casi no varían entre inmuebles"
        )
    if not diferenciadores.empty:
        aporte = diferenciadores['aporte_pct'].sum()
        partes.append(
            f"{len(diferenciadores)} actúan como factores diferenciadores y suman el "
            f"{_num(aporte, 1)}%: son los que explican las diferencias entre predios"
        )
    return '; '.join(partes).capitalize() + '.'


def nota_metodo_diagnostico():
    return (
        "La correlación se calcula entre el puntaje del indicador secundario y el índice de "
        "riesgo <i>descontado su propio aporte</i>: correlacionarlo contra el índice completo lo "
        "inflaría, porque el total contiene a la parte. Un indicador secundario en el que todos "
        "los inmuebles puntúan igual aparece con correlación cero por construcción, marcado en "
        "rojo. El porcentaje de aporte depende de los ponderadores fijados por la unidad "
        "técnica, no de los datos: describe cuánto pesa cada factor en el método, no cuánto "
        "importa en la realidad física."
    )


# ── Territorial ──────────────────────────────────────────────────────────────

def parrafo_territorial(df, ctx):
    criticas = df[df['pct_alto_mas'] >= 100]
    total_mz = len(df)
    if criticas.empty:
        return (
            f"El sitio se organiza en {total_mz} manzanas con al menos un inmueble evaluado. "
            f"Ninguna concentra la totalidad de sus inmuebles en riesgo alto o muy alto."
        )
    return (
        f"El sitio se organiza en {total_mz} manzanas con al menos un inmueble evaluado. "
        f"{len(criticas)} de ellas tienen la totalidad de sus inmuebles en riesgo alto o muy "
        f"alto, agrupando {int(criticas['n_evaluados'].sum())} predios. Intervenir por manzana, "
        f"y no predio a predio, permite además actuar sobre el contagio entre inmuebles "
        f"contiguos, que es un mecanismo que la evaluación individual no captura."
    )


# ── Inmuebles críticos ───────────────────────────────────────────────────────

def parrafo_criticos(df, ctx, n):
    if df.empty:
        return "No hay inmuebles evaluados para esta amenaza."
    peor = df.iloc[0]
    return (
        f"Los {min(n, len(df))} inmuebles de mayor índice frente a la amenaza "
        f"{ctx.nombre_amenaza.lower()}, con los factores que más aportan a su puntaje. "
        f"Encabeza la lista {peor['direccion']} (rol {peor['rol_sii']}), con un índice de "
        f"{_num(peor['indice_de_riesgo'])}. La columna de factores indica sobre qué actuar en "
        f"cada caso: no todos los inmuebles de la lista tienen el mismo problema."
    )


def nota_criticos():
    return (
        "Este listado identifica inmuebles y su condición de vulnerabilidad. Se entrega para "
        "priorizar la acción pública y su circulación debe restringirse a ese uso."
    )


def parrafo_anexo_altos(n, ctx):
    return (
        f"Los {n} inmuebles con índice de riesgo alto o muy alto frente a la amenaza "
        f"{ctx.nombre_amenaza.lower()}, ordenados de mayor a menor."
    )


# ── Multi-amenaza ────────────────────────────────────────────────────────────

def parrafo_multiamenaza(df):
    a = df.attrs['nombre_a']
    b = df.attrs['nombre_b']
    r = df.attrs['correlacion']
    n_ambas = df.attrs['n_ambas']
    n_altos = df.attrs['n_altos_en_ambas']

    if r != r:  # NaN
        relacion = "No hay suficientes inmuebles evaluados en ambas amenazas para estimar su relación"
    elif r >= 0.7:
        relacion = (f"Los índices están fuertemente correlacionados (r = {_num(r)}): en buena "
                    f"medida afectan a los mismos inmuebles")
    elif r >= 0.3:
        relacion = (f"Los índices están moderadamente correlacionados (r = {_num(r)}): las dos "
                    f"amenazas afectan en parte a los mismos inmuebles, pero no son el mismo "
                    f"problema y reducir una no reduce automáticamente la otra")
    else:
        relacion = (f"Los índices apenas se relacionan (r = {_num(r)}): son problemas "
                    f"independientes y exigen estrategias separadas")

    return (
        f"{n_ambas} inmuebles cuentan con evaluación para {a.lower()} y {b.lower()}. "
        f"{relacion}. {n_altos} inmuebles alcanzan riesgo alto o muy alto en ambas amenazas "
        f"simultáneamente: son los que deberían encabezar cualquier priorización, porque una "
        f"sola intervención sobre ellos reduce exposición frente a dos amenazas."
    )


# ── Acciones ─────────────────────────────────────────────────────────────────

def acciones(ctx):
    """Acciones derivadas de los hallazgos, en orden de retorno esperado."""
    from .analytics import DIFERENCIADOR, SISTEMICO

    salida = []
    diag = ctx.diagnostico

    if not diag.empty:
        sistemicos = diag[diag['clasificacion'] == SISTEMICO]
        if not sistemicos.empty:
            nombres = ', '.join(f"'{n}'" for n in sistemicos['subindicador_nombre'].head(3))
            salida.append(
                f"Abordar de forma programática los déficits sistémicos ({nombres} y otros "
                f"{max(len(sistemicos) - 3, 0)}). Al afectar a casi todos los inmuebles por igual, "
                f"una sola medida de alcance general mueve el índice del conjunto del sitio."
            )
        diferenciadores = diag[diag['clasificacion'] == DIFERENCIADOR]
        if not diferenciadores.empty:
            salida.append(
                f"Focalizar la intervención física en los {len(diferenciadores)} factores "
                f"diferenciadores, usando el listado de inmuebles críticos para decidir el orden."
            )

    terr = ctx.territorial
    if not terr.empty:
        criticas = terr[terr['pct_alto_mas'] >= 100].head(5)
        if not criticas.empty:
            nombres = ', '.join(str(m) for m in criticas['manzana'])
            salida.append(
                f"Priorizar territorialmente las manzanas {nombres}, donde la totalidad de los "
                f"inmuebles evaluados está en riesgo alto o muy alto."
            )

    cruce = ctx.cruce
    if cruce is not None and cruce.attrs['n_altos_en_ambas']:
        salida.append(
            f"Anteponer los {cruce.attrs['n_altos_en_ambas']} inmuebles con riesgo alto en "
            f"{cruce.attrs['nombre_a'].lower()} y {cruce.attrs['nombre_b'].lower()} a la vez, "
            f"por su exposición acumulada."
        )

    dist = ctx.distribucion
    if dist and dist['n'] < ctx.total_inmuebles:
        salida.append(
            f"Completar la evaluación de los {ctx.total_inmuebles - dist['n']} predios "
            f"pendientes, para cerrar el catastro y poder comparar entre periodos."
        )

    return salida


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
