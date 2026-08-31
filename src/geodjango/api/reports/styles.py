"""Estilos, geometría y utilidades de composición del informe."""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, KeepTogether, Paragraph, Table, TableStyle

from . import niveles


MARGIN = 1.8 * cm
USABLE_W = A4[0] - 2 * MARGIN

_ss = getSampleStyleSheet()

#: Times es una de las 14 fuentes estándar de PDF: no requiere embeber
#: archivos de letra ni arriesga fallos de renderizado. Es la convención
#: tipográfica de un informe técnico/institucional impreso.
_SERIF = 'Times-Roman'
_SERIF_NEGRITA = 'Times-Bold'
_SERIF_CURSIVA = 'Times-Italic'

TITULO = ParagraphStyle('Titulo', parent=_ss['Title'], fontName=_SERIF_NEGRITA,
                        fontSize=19, leading=23)
SUBTITULO = ParagraphStyle('Subtitulo', parent=_ss['Title'], fontName=_SERIF,
                           fontSize=12.5, leading=16, textColor=colors.HexColor('#5b5f60'))
H1 = ParagraphStyle('H1', parent=_ss['Heading1'], fontName=_SERIF_NEGRITA,
                    fontSize=14.5, spaceBefore=18, spaceAfter=8)
H2 = ParagraphStyle('H2', parent=_ss['Heading2'], fontName=_SERIF_NEGRITA,
                    fontSize=11.5, spaceBefore=12, spaceAfter=5)
#: Título de un bloque compacto. No entra al índice: H1 y H2 sí, H3 no, para que
#: el índice no se llene con una entrada por cada indicador.
H3 = ParagraphStyle('H3', parent=_ss['Heading3'], fontName=_SERIF_NEGRITA,
                    fontSize=10, spaceBefore=8, spaceAfter=3)
BODY = ParagraphStyle('Body', parent=_ss['BodyText'], fontName=_SERIF,
                      fontSize=9.8, leading=13.6, alignment=TA_JUSTIFY, spaceAfter=4)
CAPTION = ParagraphStyle('Caption', parent=_ss['BodyText'], fontName=_SERIF_CURSIVA,
                         fontSize=8.5, alignment=TA_CENTER,
                         textColor=colors.HexColor('#555555'), spaceBefore=4, spaceAfter=10)
NOTA = ParagraphStyle('Nota', parent=_ss['BodyText'], fontName=_SERIF,
                      fontSize=8.3, leading=11.5,
                      textColor=colors.HexColor('#5b5f60'), spaceBefore=4)
CELDA = ParagraphStyle('Celda', parent=_ss['BodyText'], fontName=_SERIF, fontSize=7, leading=8.6)

#: Párrafo de detalle dentro de un bloque compacto (mapa · tabla · dona).
#: Un punto más chico que BODY para que quepa junto a la figura.
DETALLE = ParagraphStyle('Detalle', parent=BODY, fontSize=8.8, leading=12, spaceAfter=6)

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


#: Ancho del mapa en la figura compacta, como fracción del ancho útil.
_COMPACTA_MAPA = 0.40
_COMPACTA_DONA = 0.30
_COMPACTA_TABLA = 0.26


def figura_compacta(titulo, map_png, tabla_flow, donut_png, pie, texto=None):
    """Bloque de media página: título, párrafo opcional, mapa · tabla · dona.

    Dos de estos caben en una página. La versión de página completa apila la
    tabla sobre la dona a la derecha del mapa; aquí los tres van en línea, lo
    que baja la altura a poco más de un tercio de la página.

    `texto` es un párrafo de detalle (estilo `DETALLE`) que se inserta entre
    el título y la fila de figuras. Va dentro del mismo `KeepTogether` que el
    resto del bloque, así el conjunto título+texto+figura nunca se parte
    entre dos páginas.
    """
    fila = Table(
        [[imagen(map_png, USABLE_W * _COMPACTA_MAPA),
          tabla_flow,
          imagen(donut_png, USABLE_W * _COMPACTA_DONA)]],
        colWidths=[USABLE_W * _COMPACTA_MAPA + 0.15 * cm,
                   USABLE_W * _COMPACTA_TABLA + 0.15 * cm,
                   USABLE_W * _COMPACTA_DONA],
    )
    fila.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    partes = [Paragraph(titulo, H3)]
    if texto:
        partes.append(Paragraph(texto, DETALLE))
    partes += [fila, Paragraph(pie, CAPTION)]
    return KeepTogether(partes)


def ancho_tabla_compacta():
    """Ancho que debe pedir la tabla resumen dentro de una figura compacta."""
    return USABLE_W * _COMPACTA_TABLA


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
