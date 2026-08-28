"""Estilos, geometría y utilidades de composición del informe."""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, Table, TableStyle

from . import niveles


MARGIN = 1.8 * cm
USABLE_W = A4[0] - 2 * MARGIN

_ss = getSampleStyleSheet()

TITULO = ParagraphStyle('Titulo', parent=_ss['Title'], fontSize=18, leading=22)
SUBTITULO = ParagraphStyle('Subtitulo', parent=_ss['Title'], fontSize=12, leading=16,
                           textColor=colors.HexColor('#5b5f60'))
H1 = ParagraphStyle('H1', parent=_ss['Heading1'], fontSize=14, spaceBefore=14, spaceAfter=6)
H2 = ParagraphStyle('H2', parent=_ss['Heading2'], fontSize=11.5, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle('Body', parent=_ss['BodyText'], fontSize=9.5, leading=13, alignment=TA_JUSTIFY)
CAPTION = ParagraphStyle('Caption', parent=_ss['BodyText'], fontSize=8.5, alignment=TA_CENTER,
                         textColor=colors.HexColor('#555555'), spaceBefore=4, spaceAfter=10)
NOTA = ParagraphStyle('Nota', parent=_ss['BodyText'], fontSize=8, leading=11,
                      textColor=colors.HexColor('#5b5f60'), spaceBefore=4)
CELDA = ParagraphStyle('Celda', parent=_ss['BodyText'], fontSize=7, leading=8.6)

#: Recuadro de hallazgo del resumen ejecutivo.
HALLAZGO = ParagraphStyle('Hallazgo', parent=BODY, fontSize=9.5, leading=13,
                          leftIndent=8, spaceBefore=2, spaceAfter=2)

GRIS = colors.HexColor('#888888')
GRIS_SUAVE = colors.HexColor('#dddddd')
FONDO_CABECERA = colors.HexColor('#eef1f2')


def imagen(png_bytes, ancho):
    """Image de ReportLab conservando la proporción del PNG."""
    iw, ih = ImageReader(BytesIO(png_bytes)).getSize()
    return Image(BytesIO(png_bytes), width=ancho, height=ancho * ih / iw)


def color_celda(nivel):
    return colors.HexColor(niveles.color(nivel))


def texto_contraste(nivel):
    """Blanco sobre los rojos, negro sobre verde, amarillo y gris."""
    return colors.white if nivel in (niveles.NIVEL_ALTO, niveles.NIVEL_MUY_ALTO) else colors.black


def color_texto_nivel(nivel):
    """Versión oscura del color del nivel, legible sobre blanco."""
    return colors.HexColor(niveles.color_texto(nivel))


def parrafo_celda(txt, estilo=None):
    return Paragraph(str(txt), estilo or CELDA)


def gdf_coloreado(base_gdf, df_niveles, columna='nivel'):
    """Une niveles al GeoDataFrame base y agrega la columna 'color'."""
    unido = base_gdf.merge(df_niveles, on='id_inmueble', how='left')
    unido[columna] = unido[columna].fillna(niveles.NIVEL_NO_EVALUADO)
    unido['color'] = unido[columna].map(niveles.color)
    return unido


def figura_compuesta(map_png, tabla_flow, donut_png):
    """Mapa a la izquierda (alto), tabla arriba a la derecha, dona abajo."""
    left_w = USABLE_W * 0.55
    right_w = USABLE_W * 0.43
    data = [[imagen(map_png, left_w), tabla_flow], ['', imagen(donut_png, right_w)]]
    t = Table(data, colWidths=[left_w + 0.2 * cm, right_w])
    t.setStyle(TableStyle([
        ('SPAN', (0, 0), (0, 1)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    return t


def grid_donas(donut_pngs, columnas=2):
    """Grilla de donas."""
    w = USABLE_W * (0.96 / columnas)
    imgs = [imagen(p, w) for p in donut_pngs]
    filas = []
    for i in range(0, len(imgs), columnas):
        fila = list(imgs[i:i + columnas])
        fila += [''] * (columnas - len(fila))
        filas.append(fila)
    t = Table(filas, colWidths=[w + 0.2 * cm] * columnas)
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    return t
