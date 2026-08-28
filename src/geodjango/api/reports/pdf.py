"""Orquestador del informe.

Recorre las secciones aplicables al modo pedido y las concatena. Las secciones
no saben en qué página caen ni qué va antes o después: el salto de página lo
pone este módulo.
"""

from reportlab.platypus import PageBreak

from . import charts, doctemplate, sections
from .config import MODO_EJECUTIVO, ReportConfig
from .context import ReportContext


def generar(cfg):
    """Genera el informe y devuelve sus bytes."""
    try:
        ctx = ReportContext(cfg)
        story = []
        for sec in sections.secciones_para(cfg, ctx):
            bloque = sec.build(ctx, cfg)
            if not bloque:
                continue
            if sec.salto_previo and story:
                story.append(PageBreak())
            story.extend(bloque)

        modo = 'Versión ejecutiva' if cfg.modo == MODO_EJECUTIVO else 'Versión completa'
        return doctemplate.construir(
            story,
            titulo=f'Riesgo de {ctx.nombre_amenaza} — Valparaíso',
            subtitulo=f'Sitio Patrimonio Mundial de Valparaíso · {modo}',
            restringido=cfg.restringido,
            con_indice=cfg.incluir_indice,
        )
    finally:
        # La caché de teselas es estado de módulo y el worker de Celery es de
        # larga vida: sin limpiarla, un informe sobre otra extensión reutilizaría
        # las teselas del anterior.
        charts.limpiar_cache()


def generar_pdf_resumen(amenaza_id, modo=MODO_EJECUTIVO, **opciones):
    """Entrada compatible con la firma anterior."""
    return generar(ReportConfig(amenaza_id=int(amenaza_id), modo=modo, **opciones))
