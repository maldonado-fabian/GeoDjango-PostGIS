"""Armado del documento: plantilla de página, índice y numeración.

El informe anterior usaba `SimpleDocTemplate` sin callbacks, así que un
documento de 26 páginas salía sin número de página, sin encabezado y sin índice.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph
from reportlab.platypus.tableofcontents import TableOfContents

from . import charts
from .styles import MARGIN


ALTO_CABECERA = 1.0 * cm
ALTO_PIE = 1.1 * cm

ESTILO_INDICE = [
    ParagraphStyle('Idx0', fontSize=10, leading=15, spaceBefore=5, leftIndent=0),
    ParagraphStyle('Idx1', fontSize=9, leading=13, leftIndent=14, textColor=colors.HexColor('#5b5f60')),
]


class InformeDocTemplate(BaseDocTemplate):
    """Plantilla con cabecera, pie numerado y soporte de índice.

    El índice necesita dos pasadas (`multiBuild`): la primera descubre en qué
    página cae cada título y la segunda lo escribe.
    """

    def __init__(self, buf, *, titulo, subtitulo, restringido=False, **kw):
        super().__init__(
            buf, pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN + ALTO_CABECERA, bottomMargin=MARGIN + ALTO_PIE,
            title=titulo, author='Unidad de Gestión de Riesgo', **kw,
        )
        self.titulo = titulo
        self.subtitulo = subtitulo
        self.restringido = restringido

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
        canvas.saveState()
        if self.restringido:
            canvas.setFont('Helvetica', 7)
            canvas.setFillColor(colors.HexColor('#8a8a8a'))
            canvas.drawCentredString(
                A4[0] / 2, MARGIN * 0.6,
                'Documento de circulación restringida · contiene identificación de inmuebles',
            )
        canvas.restoreState()

    def _decorar(self, canvas, doc):
        canvas.saveState()
        y = A4[1] - MARGIN - 0.25 * cm

        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(colors.HexColor('#5b5f60'))
        canvas.drawString(MARGIN, y, self.subtitulo)
        canvas.drawRightString(A4[0] - MARGIN, y, self.titulo)

        canvas.setStrokeColor(colors.HexColor('#cccccc'))
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN, y - 0.16 * cm, A4[0] - MARGIN, y - 0.16 * cm)

        pie_y = MARGIN * 0.75
        canvas.line(MARGIN, pie_y + 0.34 * cm, A4[0] - MARGIN, pie_y + 0.34 * cm)
        canvas.setFont('Helvetica', 7.5)
        canvas.drawCentredString(A4[0] / 2, pie_y, str(canvas.getPageNumber()))

        if self.restringido:
            canvas.setFont('Helvetica', 6.5)
            canvas.setFillColor(colors.HexColor('#a0a0a0'))
            canvas.drawString(MARGIN, pie_y, 'Circulación restringida')

        if charts.basemap_degradado:
            canvas.setFont('Helvetica-Oblique', 6.5)
            canvas.setFillColor(colors.HexColor('#a33f00'))
            canvas.drawRightString(A4[0] - MARGIN, pie_y, 'Mapas sin cartografía base')

        canvas.restoreState()

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


def construir(story, *, titulo, subtitulo, restringido=False, con_indice=True):
    """Arma el PDF y devuelve sus bytes."""
    buf = BytesIO()
    doc = InformeDocTemplate(buf, titulo=titulo, subtitulo=subtitulo, restringido=restringido)
    if con_indice:
        # Dos pasadas para resolver los números de página del índice.
        doc.multiBuild(story)
    else:
        doc.build(story)
    return buf.getvalue()
