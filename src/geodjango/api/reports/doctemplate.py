"""Armado del documento: plantilla de página, índice y numeración.

El informe original usaba `SimpleDocTemplate` sin callbacks, así que un
documento de 26 páginas salía sin número de página, sin encabezado y sin
índice. Al introducir `BaseDocTemplate` con dos `PageTemplate` (portada y
cuerpo) faltó además insertar `NextPageTemplate('cuerpo')`: sin eso,
`BaseDocTemplate` usa la primera plantilla de la lista en **todas** las
páginas, así que el encabezado/pie nunca llegó a dibujarse en ningún informe
generado hasta ahora. Verificado con un documento de prueba aislado antes de
corregirlo.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as canvas_mod
from reportlab.platypus import BaseDocTemplate, Frame, NextPageTemplate, PageTemplate, Paragraph
from reportlab.platypus.tableofcontents import TableOfContents

from . import charts
from .styles import MARGIN


ALTO_CABECERA = 1.0 * cm
ALTO_PIE = 1.1 * cm

ESTILO_INDICE = [
    ParagraphStyle('Idx0', fontName='Times-Bold', fontSize=10, leading=15,
                   spaceBefore=6, leftIndent=0),
    ParagraphStyle('Idx1', fontName='Times-Roman', fontSize=9, leading=13,
                   leftIndent=14, textColor=colors.HexColor('#5b5f60')),
]


def _dibujar_pie(canvas, titulo, subtitulo, numero_pagina, total_paginas):
    """Encabezado, regla, pie con "Página X de Y" y aviso de mapa base si aplica."""
    canvas.saveState()
    y = A4[1] - MARGIN - 0.25 * cm

    canvas.setFont('Times-Roman', 7.5)
    canvas.setFillColor(colors.HexColor('#5b5f60'))
    canvas.drawString(MARGIN, y, subtitulo)
    canvas.drawRightString(A4[0] - MARGIN, y, titulo)

    canvas.setStrokeColor(colors.HexColor('#999999'))
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, y - 0.16 * cm, A4[0] - MARGIN, y - 0.16 * cm)

    pie_y = MARGIN * 0.75
    canvas.line(MARGIN, pie_y + 0.34 * cm, A4[0] - MARGIN, pie_y + 0.34 * cm)
    canvas.setFont('Times-Roman', 7.5)
    texto_pagina = f'Página {numero_pagina} de {total_paginas}' if total_paginas else str(numero_pagina)
    canvas.drawCentredString(A4[0] / 2, pie_y, texto_pagina)

    if charts.basemap_degradado:
        canvas.setFont('Times-Italic', 6.5)
        canvas.setFillColor(colors.HexColor('#a33f00'))
        canvas.drawRightString(A4[0] - MARGIN, pie_y, 'Mapas sin cartografía base')

    canvas.restoreState()


class _CanvasNumerado(canvas_mod.Canvas):
    """Difiere el sello de "Página X de Y" hasta `save()`, cuando ya se conoce
    el total de páginas.

    Técnica estándar de ReportLab: cada `showPage()` guarda el estado del
    canvas en vez de cerrarlo; recién en `save()`, con el conteo final, se
    recorre cada estado guardado, se dibuja el pie con el total correcto y
    ahí sí se cierra la página.

    La portada (página 1) no lleva pie: se distingue por convención de que
    `InformeDocTemplate._portada` no llama a `_dibujar_pie`, así que su
    estado guardado simplemente no incluye esa marca.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._paginas_pendientes = []
        # Rellenado por InformeDocTemplate en cada onPage: (titulo, subtitulo)
        # o None si la página no debe llevar pie (la portada).
        self.pie_pendiente = None

    def showPage(self):
        self._paginas_pendientes.append((dict(self.__dict__), self.pie_pendiente))
        self.pie_pendiente = None
        self._startPage()

    def save(self):
        total = len(self._paginas_pendientes)
        for estado, pie in self._paginas_pendientes:
            self.__dict__.update(estado)
            if pie is not None:
                titulo, subtitulo = pie
                _dibujar_pie(self, titulo, subtitulo, self._pageNumber, total)
            canvas_mod.Canvas.showPage(self)
        canvas_mod.Canvas.save(self)


class InformeDocTemplate(BaseDocTemplate):
    """Plantilla con cabecera, pie "Página X de Y" e índice.

    El índice necesita dos pasadas (`multiBuild`): la primera descubre en qué
    página cae cada título y la segunda lo escribe. El total de páginas para
    el pie se resuelve aparte, en `_CanvasNumerado.save()`, sobre la versión
    final ya construida.
    """

    def __init__(self, buf, *, titulo, subtitulo, **kw):
        super().__init__(
            buf, pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN + ALTO_CABECERA, bottomMargin=MARGIN + ALTO_PIE,
            title=titulo, author='Unidad de Gestión de Riesgo', **kw,
        )
        self.titulo = titulo
        self.subtitulo = subtitulo

        marco = Frame(
            self.leftMargin, self.bottomMargin,
            self.width, self.height, id='cuerpo',
        )
        self.addPageTemplates([
            PageTemplate(id='portada', frames=[marco], onPage=self._portada),
            PageTemplate(id='cuerpo', frames=[marco], onPage=self._decorar),
        ])

    # ── decoración de página ─────────────────────────────────────────────────

    def _portada(self, canvas, doc):
        """La portada no lleva cabecera ni numeración."""
        canvas.pie_pendiente = None

    def _decorar(self, canvas, doc):
        canvas.pie_pendiente = (self.titulo, self.subtitulo)

    # ── índice ───────────────────────────────────────────────────────────────

    def afterFlowable(self, flowable):
        """Registra los títulos para el índice y para los marcadores del PDF."""
        if not isinstance(flowable, Paragraph):
            return
        estilo = flowable.style.name
        if estilo not in ('H1', 'H2'):
            return

        nivel = 0 if estilo == 'H1' else 1
        texto = flowable.getPlainText()
        clave = f'sec-{id(flowable)}'
        self.canv.bookmarkPage(clave)
        self.canv.addOutlineEntry(texto, clave, level=nivel, closed=(nivel > 0))
        self.notify('TOCEntry', (nivel, texto, self.page, clave))


def indice():
    """Flowable del índice."""
    toc = TableOfContents()
    toc.levelStyles = ESTILO_INDICE
    return toc


def construir(story, *, titulo, subtitulo, con_indice=True):
    """Arma el PDF y devuelve sus bytes.

    Inserta `NextPageTemplate('cuerpo')` justo después de la portada: sin él,
    `BaseDocTemplate` se queda en la primera plantilla (portada, sin pie) para
    todo el documento en vez de pasar a la plantilla con encabezado y pie a
    partir de la segunda página.
    """
    buf = BytesIO()
    doc = InformeDocTemplate(buf, titulo=titulo, subtitulo=subtitulo)

    story_completa = list(story)
    story_completa.insert(0, NextPageTemplate('cuerpo'))

    if con_indice:
        # Dos pasadas para resolver los números de página del índice.
        doc.multiBuild(story_completa, canvasmaker=_CanvasNumerado)
    else:
        doc.build(story_completa, canvasmaker=_CanvasNumerado)
    return buf.getvalue()
