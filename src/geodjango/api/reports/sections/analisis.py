"""Diagnóstico de los factores de riesgo.

Qué factores exigen una acción única para todo el sitio y cuáles, una
intervención predio a predio. Se aplica en dos niveles: los indicadores
primarios, que es el nivel al que se toman las decisiones de programa, y sus
sub-indicadores, que es el nivel al que se define la obra concreta.
"""

from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

from .. import analytics, charts, tables, text
from ..styles import BODY, CAPTION, H1, H2, NOTA, USABLE_W, imagen
from . import seccion


def _p(txt, estilo=BODY):
    return Paragraph(txt, estilo)


def _fig(png, ancho=0.94):
    return imagen(png, USABLE_W * ancho)


def _bloque_diagnostico(ctx, cfg, df, etiqueta_tabla, titulo_grafico):
    """Barras, dispersión y tablas de un nivel de diagnóstico."""
    return [
        _fig(charts.barras_aporte(df, titulo_grafico, dpi=cfg.dpi_dona)),
        _p(f'Figura {ctx.figura.siguiente()}. Aporte al índice, coloreado por clasificación.',
           CAPTION),
        _p(text.parrafo_diagnostico(df), BODY),
        Spacer(1, 0.3 * cm),
        _fig(charts.dispersion_aporte_correlacion(
            df, 'APORTE FRENTE A CAPACIDAD DE DISCRIMINAR',
            umbral_correlacion=cfg.umbral_correlacion, dpi=cfg.dpi_dona), 0.84),
        _p(f'Figura {ctx.figura.siguiente()}. Cada punto es un factor; el número corresponde '
           f'a su fila en la tabla siguiente.', CAPTION),
        Spacer(1, 0.25 * cm),
        tables.diagnostico(df, etiqueta=etiqueta_tabla),
        _p(f'Tabla {ctx.tabla.siguiente()}. Detalle ordenado por aporte al índice.', CAPTION),
    ]


@seccion('diagnostico_primarios', 'Qué explica el riesgo: indicadores primarios', 500,
         requiere=('diagnostico',))
def diagnostico_primarios(ctx, cfg):
    df = ctx.diagnostico_indicadores
    return [
        _p('Qué factores explican el riesgo', H1),
        _p(text.intro_diagnostico(), BODY),
        Spacer(1, 0.25 * cm),
        _p('Indicadores primarios', H2),
        *_bloque_diagnostico(ctx, cfg, df, 'INDICADOR',
                             'APORTE DE CADA INDICADOR PRIMARIO AL ÍNDICE'),
        Spacer(1, 0.25 * cm),
        tables.clasificacion_resumen(df, analytics.DESCRIPCION_CLASIFICACION),
        _p(f'Tabla {ctx.tabla.siguiente()}. Qué implica cada clasificación.', CAPTION),
    ]


@seccion('diagnostico_secundarios', 'Qué explica el riesgo: indicadores secundarios', 550,
         requiere=('diagnostico',))
def diagnostico_secundarios(ctx, cfg):
    df = ctx.diagnostico
    return [
        _p('Indicadores secundarios', H2),
        _p(text.intro_diagnostico_secundarios(), BODY),
        Spacer(1, 0.2 * cm),
        *_bloque_diagnostico(ctx, cfg, df, 'SUB-INDICADOR',
                             'APORTE DE CADA INDICADOR SECUNDARIO AL ÍNDICE'),
        _p(text.nota_metodo_diagnostico(), NOTA),
    ]
