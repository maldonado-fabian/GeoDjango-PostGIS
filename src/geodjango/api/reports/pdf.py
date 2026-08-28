"""Ensamblado del PDF de resumen global de riesgo con ReportLab Platypus."""

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from . import charts, niveles, queries, text

_MARGIN = 1.8 * cm
_USABLE_W = A4[0] - 2 * _MARGIN

# ── estilos ──────────────────────────────────────────────────────────────────
_ss = getSampleStyleSheet()
_TITULO = ParagraphStyle("Titulo", parent=_ss["Title"], fontSize=18, leading=22)
_H1 = ParagraphStyle("H1", parent=_ss["Heading1"], fontSize=14, spaceBefore=14, spaceAfter=6)
_H2 = ParagraphStyle("H2", parent=_ss["Heading2"], fontSize=11.5, spaceBefore=10, spaceAfter=4)
_BODY = ParagraphStyle("Body", parent=_ss["BodyText"], fontSize=9.5, leading=13, alignment=TA_JUSTIFY)
_CAPTION = ParagraphStyle("Caption", parent=_ss["BodyText"], fontSize=8.5, alignment=TA_CENTER,
                          textColor=colors.HexColor("#555555"), spaceBefore=4, spaceAfter=10)


# ── helpers ──────────────────────────────────────────────────────────────────
def _image(png_bytes, width):
    """Crea un Image de ReportLab conservando la proporción del PNG."""
    iw, ih = ImageReader(BytesIO(png_bytes)).getSize()
    return Image(BytesIO(png_bytes), width=width, height=width * ih / iw)


def _gdf_coloreado(base_gdf, df_niveles):
    """Une niveles al GeoDataFrame base y agrega columna 'color' por fila."""
    merged = base_gdf.merge(df_niveles, on="id_inmueble", how="left")
    merged["nivel"] = merged["nivel"].fillna(niveles.NIVEL_NO_EVALUADO)
    merged["color"] = merged["nivel"].map(niveles.color)
    return merged


#: Largo máximo de una etiqueta de clase en la leyenda del mapa. Por encima de
#: esto el recuadro se come la figura.
_MAX_ETIQUETA = 34


def _etiqueta_clase(etiquetas, subindicador_id, valor):
    """Nombre de la clase para un puntaje, o el puntaje si no hay clase definida."""
    nombre = (etiquetas.get(int(subindicador_id)) or {}).get(int(valor))
    if not nombre:
        return str(valor)
    if len(nombre) > _MAX_ETIQUETA:
        nombre = nombre[:_MAX_ETIQUETA - 1].rstrip() + "…"
    return f"{valor} · {nombre}"


def _cell_color(nivel):
    return colors.HexColor(niveles.color(nivel))


def _texto_contraste(nivel):
    # texto blanco sobre rojos, negro sobre verde/amarillo/gris
    return colors.white if nivel in (niveles.NIVEL_ALTO, niveles.NIVEL_MUY_ALTO) else colors.black


# ── tablas ───────────────────────────────────────────────────────────────────
def _tabla_evaluacion(filas, total, titulo="EVALUACIÓN GLOBAL", ancho=None):
    """Tabla ESCALA / Nº / % para una amenaza/indicador (Figura 1b / 3b)."""
    ancho = ancho or _USABLE_W * 0.42
    data = [[titulo, "", ""], ["ESCALA", "Nº", "%"]]
    estilos = [
        ("SPAN", (0, 0), (2, 0)),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#ffffff")),
    ]
    for i, f in enumerate(filas):
        r = i + 2
        data.append([f["nivel"].upper(), str(f["cantidad"]), str(f["porcentaje"])])
        estilos.append(("BACKGROUND", (0, r), (0, r), _cell_color(f["nivel"])))
        estilos.append(("TEXTCOLOR", (0, r), (0, r), _texto_contraste(f["nivel"])))
        estilos.append(("FONTNAME", (0, r), (0, r), "Helvetica-Bold"))
    rt = len(data)
    data.append(["TOTAL", str(total), "100"])
    estilos.append(("FONTNAME", (0, rt), (-1, rt), "Helvetica-Bold"))
    col = ancho / 3
    t = Table(data, colWidths=[col * 1.5, col * 0.75, col * 0.75])
    t.setStyle(TableStyle(estilos))
    return t


def _tabla1(amenazas_data, total):
    """Tabla 1 global con columnas dinámicas por amenaza."""
    # fila 0: encabezados de amenaza (cada uno ocupa 2 columnas)
    fila_amenaza = [""]
    fila_subhdr = ["ESCALA"]
    for a in amenazas_data:
        fila_amenaza += [a["nombre"], ""]
        fila_subhdr += ["Nº", "%"]
    data = [fila_amenaza, fila_subhdr]

    for nivel in niveles.NIVELES:
        fila = [nivel.upper()]
        for a in amenazas_data:
            f = next((x for x in a["filas"] if x["nivel"] == nivel), {"cantidad": 0, "porcentaje": 0})
            fila += [str(f["cantidad"]), str(f["porcentaje"])]
        data.append(fila)
    # TOTAL
    fila_total = ["TOTAL"]
    for _ in amenazas_data:
        fila_total += [str(total), "100"]
    data.append(fila_total)
    # fila dominante
    fila_dom = [""]
    for a in amenazas_data:
        fila_dom += [a["dominante"].upper() if a["dominante"] else "", ""]
    data.append(fila_dom)

    n_dom = len(data) - 1
    estilos = [
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#888888")),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTNAME", (0, len(niveles.NIVELES) + 2), (-1, len(niveles.NIVELES) + 2), "Helvetica-Bold"),
    ]
    # SPAN encabezados de amenaza + color nivel en la primera columna
    for idx in range(len(amenazas_data)):
        c0 = 1 + idx * 2
        estilos.append(("SPAN", (c0, 0), (c0 + 1, 0)))
    for i, nivel in enumerate(niveles.NIVELES):
        r = i + 2
        estilos.append(("BACKGROUND", (0, r), (0, r), _cell_color(nivel)))
        estilos.append(("TEXTCOLOR", (0, r), (0, r), _texto_contraste(nivel)))
        estilos.append(("FONTNAME", (0, r), (0, r), "Helvetica-Bold"))
    # resaltar la celda dominante (fila inferior)
    for idx, a in enumerate(amenazas_data):
        if a["dominante"]:
            c0 = 1 + idx * 2
            estilos.append(("SPAN", (c0, n_dom), (c0 + 1, n_dom)))
            estilos.append(("BACKGROUND", (c0, n_dom), (c0 + 1, n_dom), _cell_color(a["dominante"])))
            estilos.append(("TEXTCOLOR", (c0, n_dom), (c0 + 1, n_dom), _texto_contraste(a["dominante"])))
            estilos.append(("FONTNAME", (c0, n_dom), (c0 + 1, n_dom), "Helvetica-Bold"))

    ncols = 1 + 2 * len(amenazas_data)
    col0 = _USABLE_W * 0.18
    rest = (_USABLE_W - col0) / (ncols - 1)
    t = Table(data, colWidths=[col0] + [rest] * (ncols - 1))
    t.setStyle(TableStyle(estilos))
    return t


def _tabla2():
    """Tabla 2: rangos y descriptores del índice de riesgo.

    Los rangos se derivan de los cortes canónicos (`api/riesgo.py`); antes eran
    literales y cambiar un corte desincronizaba la tabla en silencio.
    """
    rangos = [
        (niveles.rango_texto(nivel), nivel, text.DESCRIPTORES_NIVEL[nivel])
        for nivel in niveles.NIVELES_RIESGO
    ]
    data = [["RANGO", "", "DESCRIPCIÓN"]]
    estilos = [
        ("SPAN", (0, 0), (1, 0)),
        ("ALIGN", (0, 0), (1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
    ]
    desc_style = ParagraphStyle("d", parent=_BODY, fontSize=8, leading=10)
    for i, (rango, nivel, desc) in enumerate(rangos):
        r = i + 1
        data.append([rango, nivel.upper(), Paragraph(desc, desc_style)])
        estilos.append(("BACKGROUND", (1, r), (1, r), _cell_color(nivel)))
        estilos.append(("TEXTCOLOR", (1, r), (1, r), _texto_contraste(nivel)))
        estilos.append(("FONTNAME", (1, r), (1, r), "Helvetica-Bold"))
    t = Table(data, colWidths=[_USABLE_W * 0.16, _USABLE_W * 0.16, _USABLE_W * 0.68])
    t.setStyle(TableStyle(estilos))
    return t


def _figura_compuesta(map_png, tabla_flow, donut_png):
    """Layout: mapa (izq, alto) · tabla (sup-der) · dona (inf-der)."""
    left_w = _USABLE_W * 0.55
    right_w = _USABLE_W * 0.43
    map_img = _image(map_png, left_w)
    donut_img = _image(donut_png, right_w)
    data = [[map_img, tabla_flow], ["", donut_img]]
    t = Table(data, colWidths=[left_w + 0.2 * cm, right_w])
    t.setStyle(TableStyle([
        ("SPAN", (0, 0), (0, 1)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
    ]))
    return t


def _grid_donas(donut_pngs):
    """Grilla 2 columnas de donas (Figura 2)."""
    w = _USABLE_W * 0.48
    imgs = [_image(p, w) for p in donut_pngs]
    filas = []
    for i in range(0, len(imgs), 2):
        fila = imgs[i:i + 2]
        if len(fila) == 1:
            fila.append("")
        filas.append(fila)
    t = Table(filas, colWidths=[w + 0.2 * cm, w + 0.2 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    return t


class _Contador:
    """Numera figuras según el orden real de armado.

    Antes el bucle de sub-indicadores arrancaba en `start=3`, dando por hecho
    que siempre habría exactamente dos figuras antes: agregar una figura en
    cualquier punto anterior renumeraba mal todo el resto sin avisar.
    """

    def __init__(self):
        self._n = 0

    def siguiente(self):
        self._n += 1
        return self._n


# ── datos agregados ──────────────────────────────────────────────────────────
def _conteo_amenaza(amenaza_id, total):
    idx = queries.indice_por_inmueble(amenaza_id)
    nivs = [niveles.nivel_por_indice(v) for v in idx["indice_de_riesgo"]]
    filas = niveles.conteo(nivs, total)
    promedio = float(idx["indice_de_riesgo"].mean()) if len(idx) else 0.0
    return idx, filas, promedio


# ── documento ────────────────────────────────────────────────────────────────
def generar_pdf_resumen(amenaza_id):
    """Genera el PDF (bytes) del resumen global, con detalle de `amenaza_id`."""
    try:
        return _generar_pdf_resumen(amenaza_id)
    finally:
        # La caché de teselas es estado de módulo y el worker de Celery es de
        # larga vida: sin limpiarla, un informe sobre otra extensión reutilizaría
        # las teselas del anterior.
        charts.limpiar_cache()


def _generar_pdf_resumen(amenaza_id):
    amenaza_id = int(amenaza_id)

    # Fallar aquí y no más abajo: antes, un id inexistente producía un informe
    # con todas las tablas vacías pero titulado "Incendio", que es peor que un
    # error porque parece un resultado.
    amenaza_actual = queries.amenaza(amenaza_id)
    if amenaza_actual is None:
        raise ValueError(f'No existe la amenaza con id {amenaza_id}')
    nombre_amenaza = amenaza_actual['nombre']

    total = queries.total_inmuebles()
    df_amen = queries.amenazas()
    base_geo = queries.inmuebles_geo()
    etiquetas = queries.etiquetas_clase(amenaza_id)
    figura = _Contador()

    # --- agregados por amenaza (Tabla 1 + promedios) ---
    amenazas_data, promedios = [], []
    for _, a in df_amen.iterrows():
        _, filas, prom = _conteo_amenaza(int(a["id"]), total)
        amenazas_data.append({
            "id": int(a["id"]), "nombre": a["nombre"], "filas": filas,
            "dominante": niveles.dominante(filas),
        })
        promedios.append({"nombre": a["nombre"], "promedio": prom,
                          "nivel": niveles.nivel_por_indice(prom)})
    promedios.sort(key=lambda p: p["promedio"], reverse=True)

    story = []

    # 1) Portada
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph(
        "Resultados globales evaluación de riesgo<br/>Sitio Patrimonio Mundial de Valparaíso",
        _TITULO))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d-%m-%Y %H:%M')}",
        ParagraphStyle("f", parent=_BODY, alignment=TA_CENTER)))
    story.append(PageBreak())

    # 2) Resultados globales
    story.append(Paragraph("Resultados globales", _H1))
    story.append(Paragraph(text.intro_resultados_globales(list(df_amen["nombre"])), _BODY))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_tabla1(amenazas_data, total))
    story.append(Paragraph("Tabla 1. Resultados globales evaluación de riesgo.", _CAPTION))
    # De la amenaza pedida, no de la primera de la lista: la cobertura puede
    # diferir entre amenazas y antes el párrafo de un informe de Sismo citaba
    # los inmuebles evaluados de Incendio.
    filas_amenaza_actual = next(
        a["filas"] for a in amenazas_data if a["id"] == amenaza_id
    )
    no_eval = next(f["cantidad"] for f in filas_amenaza_actual
                   if f["nivel"] == niveles.NIVEL_NO_EVALUADO)
    story.append(Paragraph(text.parrafo_evaluados(total, no_eval, nombre_amenaza), _BODY))

    # 3) Tabla 2
    story.append(Spacer(1, 0.3 * cm))
    story.append(_tabla2())
    story.append(Paragraph("Tabla 2. Rangos y descriptores para el índice de riesgo.", _CAPTION))

    # 4) Promedios por amenaza
    story.append(Paragraph(text.parrafo_promedios(promedios), _BODY))

    # 5) Detalle de la amenaza objetivo
    df_ind = queries.indicadores(amenaza_id)

    story.append(PageBreak())
    story.append(Paragraph(f"Detalle de la amenaza: {nombre_amenaza}", _H1))
    story.append(Paragraph(text.detalle_amenaza_intro(nombre_amenaza, list(df_ind["nombre"])), _BODY))

    # 5.2 Resultados globales de la amenaza (Figura 1)
    idx, filas_am, _ = _conteo_amenaza(amenaza_id, total)
    story.append(Paragraph(f"Resultados globales amenaza {nombre_amenaza.lower()}", _H2))
    story.append(Paragraph(text.parrafo_resultados_amenaza(filas_am, total), _BODY))
    idx_niv = idx.copy()
    idx_niv["nivel"] = idx_niv["indice_de_riesgo"].map(niveles.nivel_por_indice)
    gdf_fig1 = _gdf_coloreado(base_geo, idx_niv[["id_inmueble", "nivel"]])
    # Incluye "No evaluado": el mapa pinta de gris los inmuebles sin evaluación,
    # y antes la leyenda no explicaba ese gris.
    leyenda_riesgo = [(n, niveles.color(n)) for n in niveles.NIVELES]
    map_png = charts.mapa(gdf_fig1, nombre_amenaza, leyenda_riesgo,
                          etiqueta_leyenda=nombre_amenaza.upper())
    donut_png = charts.donut(filas_am, "RESULTADO GLOBAL Nº; % DE EDIFICIOS")
    story.append(_figura_compuesta(map_png, _tabla_evaluacion(filas_am, total), donut_png))
    story.append(Paragraph(
        f"Figura {figura.siguiente()}. Resultado global de la amenaza {nombre_amenaza.lower()}.",
        _CAPTION))

    # 5.3 Indicadores primarios (Figura 2)
    story.append(PageBreak())
    story.append(Paragraph("Incidencia de los indicadores primarios", _H2))
    story.append(Paragraph(text.parrafo_indicadores_primarios(), _BODY))
    df_scores = queries.indicador_scores(amenaza_id)
    donas_ind = []
    for ind_id, g in df_scores.groupby("indicador_id", sort=True):
        nombre = g["indicador_nombre"].iloc[0]
        nivs = [niveles.nivel_por_indice(v) for v in g["score"]]
        filas = niveles.conteo(nivs, total)
        donas_ind.append(charts.donut(filas, f"{nombre.upper()} Nº; % DE EDIFICIOS"))
    story.append(_grid_donas(donas_ind))
    story.append(Paragraph(
        f"Figura {figura.siguiente()}. Resultados de los indicadores primarios.", _CAPTION))

    # 5.4 Indicadores secundarios (una figura compuesta por subindicador)
    story.append(PageBreak())
    story.append(Paragraph("Incidencia de los indicadores secundarios en los resultados", _H2))
    story.append(Paragraph(text.parrafo_indicadores_secundarios(), _BODY))
    df_sub = queries.subindicador_valores(amenaza_id)
    for sub_id, g in df_sub.groupby("subindicador_id", sort=True):
        nombre = g["subindicador_nombre"].iloc[0]
        # Leyenda con el nombre de la clase ("Entramado de madera") en vez del
        # puntaje desnudo ("4"), que no le dice nada al lector.
        leyenda_escala = [
            (_etiqueta_clase(etiquetas, sub_id, v),
             niveles.color(niveles.nivel_por_valor_crudo(v)))
            for v in (1, 2, 3, 4)
        ]
        nivs = [niveles.nivel_por_valor_crudo(v) for v in g["valor"]]
        filas = niveles.conteo(nivs, total)
        promedio = float(g["valor"].mean()) if len(g) else 0.0
        nivel_prom = niveles.nivel_por_indice(promedio)

        gv = g[["id_inmueble", "valor"]].copy()
        gv["nivel"] = gv["valor"].map(niveles.nivel_por_valor_crudo)
        gdf_sub = _gdf_coloreado(base_geo, gv[["id_inmueble", "nivel"]])

        # Cada subindicador comienza en su propia página
        story.append(PageBreak())
        story.append(Paragraph(f"Indicador secundario: {nombre}", _H2))
        story.append(Paragraph(text.parrafo_subindicador(nombre, promedio, nivel_prom), _BODY))
        map_png = charts.mapa(gdf_sub, nombre, leyenda_escala,
                              etiqueta_leyenda=nombre.upper())
        donut_png = charts.donut(filas, f"{nombre.upper()} Nº; % DE EDIFICIOS")
        story.append(_figura_compuesta(map_png, _tabla_evaluacion(filas, total, nombre.upper()), donut_png))
        story.append(Paragraph(
            f"Figura {figura.siguiente()}. Resultado indicador secundario «{nombre}».", _CAPTION))

    # 6) Conclusiones
    story.append(PageBreak())
    story.append(Paragraph("Conclusiones y comentarios", _H1))
    story.append(Paragraph(text.conclusiones(filas_am, nombre_amenaza), _BODY))

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=_MARGIN, rightMargin=_MARGIN, topMargin=_MARGIN, bottomMargin=_MARGIN,
        title="Resumen global de riesgo — Valparaíso",
    )
    doc.build(story)
    return buf.getvalue()
