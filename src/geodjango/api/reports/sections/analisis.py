"""Análisis que orientan la decisión.

Cuatro secciones que el informe anterior no tenía:

- `diagnostico`  separa déficits sistémicos de factores diferenciadores
- `territorial`  agrega por manzana, la unidad de gestión real
- `criticos`     nombra los inmuebles de mayor riesgo y por qué lo son
- `multiamenaza` cruza dos amenazas sobre los mismos inmuebles
"""

from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

from .. import analytics, charts, niveles, tables, text
from ..config import MODO_COMPLETO
from ..styles import BODY, CAPTION, H1, NOTA, USABLE_W, imagen
from . import seccion


def _p(txt, estilo=BODY):
    return Paragraph(txt, estilo)


def _fig(png, ancho=0.94):
    return imagen(png, USABLE_W * ancho)


@seccion('diagnostico', 'Diagnóstico de los factores de riesgo', 500,
         requiere=('diagnostico',))
def diagnostico(ctx, cfg):
    """Qué factores exigen una acción única para todo el sitio y cuáles, predio a predio."""
    df = ctx.diagnostico

    partes = [
        _p('Qué factores explican el riesgo', H1),
        _p(text.intro_diagnostico(), BODY),
        Spacer(1, 0.25 * cm),
        _fig(charts.barras_aporte(df, 'APORTE DE CADA SUB-INDICADOR AL ÍNDICE',
                                  dpi=cfg.dpi_dona)),
        _p(f'Figura {ctx.figura.siguiente()}. Aporte de cada sub-indicador, según su '
           f'clasificación.', CAPTION),
        _p(text.parrafo_diagnostico(df), BODY),
        Spacer(1, 0.3 * cm),
        _fig(charts.dispersion_aporte_correlacion(
            df, 'APORTE FRENTE A CAPACIDAD DE DISCRIMINAR',
            umbral_correlacion=cfg.umbral_correlacion, dpi=cfg.dpi_dona), 0.86),
        _p(f'Figura {ctx.figura.siguiente()}. Cada punto es un sub-indicador; el número '
           f'corresponde a su fila en la tabla siguiente.', CAPTION),
        Spacer(1, 0.25 * cm),
        tables.clasificacion_resumen(df, analytics.DESCRIPCION_CLASIFICACION),
        _p(f'Tabla {ctx.tabla.siguiente()}. Clasificación de los sub-indicadores.', CAPTION),
        Spacer(1, 0.3 * cm),
        tables.diagnostico(df),
        _p(f'Tabla {ctx.tabla.siguiente()}. Detalle por sub-indicador, ordenado por aporte.',
           CAPTION),
        _p(text.nota_metodo_diagnostico(), NOTA),
    ]
    return partes


@seccion('territorial', 'Concentración territorial', 600, requiere=('territorial',))
def territorial(ctx, cfg):
    """Dónde concentrar la intervención."""
    df = ctx.territorial
    n = cfg.top_manzanas

    manzanas = ctx.geo_manzanas.merge(
        df[['manzana', 'indice_medio', 'nivel_medio']], on='manzana', how='left')
    manzanas['nivel_medio'] = manzanas['nivel_medio'].fillna(niveles.NIVEL_NO_EVALUADO)
    manzanas['color'] = manzanas['nivel_medio'].map(niveles.color)

    leyenda = [(nivel, niveles.color(nivel)) for nivel in niveles.NIVELES]
    mapa_png = charts.mapa(manzanas, 'ÍNDICE MEDIO POR MANZANA', leyenda,
                           etiqueta_leyenda='NIVEL MEDIO', dpi=cfg.dpi_mapa,
                           basemap=cfg.basemap)

    return [
        _p('Dónde se concentra el riesgo', H1),
        _p(text.parrafo_territorial(df, ctx), BODY),
        Spacer(1, 0.25 * cm),
        _fig(mapa_png, 0.60),
        _p(f'Figura {ctx.figura.siguiente()}. Índice medio agregado por manzana.', CAPTION),
        Spacer(1, 0.2 * cm),
        _fig(charts.barras_manzanas(df, 'MANZANAS CON MAYOR PROPORCIÓN EN RIESGO ALTO',
                                    n=n, dpi=cfg.dpi_dona), 0.88),
        _p(f'Figura {ctx.figura.siguiente()}. Las {n} manzanas más críticas.', CAPTION),
        Spacer(1, 0.2 * cm),
        tables.manzanas(df, n=n),
        _p(f'Tabla {ctx.tabla.siguiente()}. Manzanas ordenadas por proporción de inmuebles '
           f'en riesgo alto o muy alto.', CAPTION),
    ]


@seccion('criticos', 'Inmuebles críticos', 700, requiere=('criticos',))
def criticos(ctx, cfg):
    """Los inmuebles que encabezan la prioridad, con el motivo."""
    df = ctx.criticos
    n = cfg.top_criticos
    return [
        _p('Inmuebles que encabezan la prioridad', H1),
        _p(text.parrafo_criticos(df, ctx, n), BODY),
        Spacer(1, 0.25 * cm),
        tables.criticos(df, n=n),
        _p(f'Tabla {ctx.tabla.siguiente()}. Los {min(n, len(df))} inmuebles de mayor índice, '
           f'con los factores que más aportan a su puntaje.', CAPTION),
        _p(text.nota_criticos(), NOTA),
    ]


@seccion('multiamenaza', 'Riesgo multi-amenaza', 800, requiere=('multi_amenaza',))
def multiamenaza(ctx, cfg):
    """Qué inmuebles acumulan riesgo alto en más de una amenaza."""
    df = ctx.cruce
    nombre_a = df.attrs['nombre_a']
    nombre_b = df.attrs['nombre_b']

    partes = [
        _p('Riesgo frente a más de una amenaza', H1),
        _p(text.parrafo_multiamenaza(df), BODY),
        Spacer(1, 0.25 * cm),
        _fig(charts.matriz_cruzada(
            df.attrs['matriz'], nombre_a, nombre_b,
            f'INMUEBLES POR NIVEL EN {nombre_a.upper()} Y {nombre_b.upper()}',
            dpi=cfg.dpi_dona), 0.52),
        _p(f'Figura {ctx.figura.siguiente()}. Contingencia entre los niveles de ambas amenazas.',
           CAPTION),
        Spacer(1, 0.2 * cm),
        _fig(charts.dispersion_amenazas(
            df, nombre_a, nombre_b,
            f'ÍNDICE {nombre_a.upper()} FRENTE A {nombre_b.upper()}',
            dpi=cfg.dpi_dona), 0.55),
        _p(f'Figura {ctx.figura.siguiente()}. Cada punto es un inmueble; el área sombreada '
           f'marca el riesgo alto en ambas amenazas.', CAPTION),
    ]

    if df.attrs['n_altos_en_ambas']:
        limite = None if cfg.modo == MODO_COMPLETO else 15
        partes += [
            Spacer(1, 0.2 * cm),
            tables.multi_amenaza(df, n=limite or df.attrs['n_altos_en_ambas']),
            _p(f'Tabla {ctx.tabla.siguiente()}. Inmuebles en riesgo alto o muy alto en ambas '
               f'amenazas.', CAPTION),
        ]
    return partes


@seccion('anexo_altos', 'Anexo: inmuebles en riesgo alto', 1200, modos=(MODO_COMPLETO,),
         requiere=('criticos',))
def anexo_altos(ctx, cfg):
    """Listado completo, no sólo los primeros."""
    from .. import analytics as an

    completo = an.criticos(ctx.contribuciones, ctx.meta, ctx.etiquetas_clase,
                           top=len(ctx.indice()))
    altos = completo[completo['nivel'].isin([niveles.NIVEL_ALTO, niveles.NIVEL_MUY_ALTO])]
    if altos.empty:
        return []
    return [
        _p('Anexo A. Inmuebles en riesgo alto o muy alto', H1),
        _p(text.parrafo_anexo_altos(len(altos), ctx), BODY),
        Spacer(1, 0.25 * cm),
        tables.criticos(altos, n=len(altos)),
        _p(f'Tabla {ctx.tabla.siguiente()}. Listado completo de inmuebles en riesgo alto '
           f'o muy alto.', CAPTION),
    ]


@seccion('anexo_manzanas', 'Anexo: todas las manzanas', 1300, modos=(MODO_COMPLETO,),
         requiere=('territorial',))
def anexo_manzanas(ctx, cfg):
    df = ctx.territorial
    return [
        _p('Anexo B. Resultado por manzana', H1),
        _p(f'Las {len(df)} manzanas del sitio con al menos un inmueble evaluado, '
           f'ordenadas por proporción de inmuebles en riesgo alto o muy alto.', BODY),
        Spacer(1, 0.25 * cm),
        tables.manzanas(df, n=len(df)),
        _p(f'Tabla {ctx.tabla.siguiente()}. Resultado agregado de todas las manzanas.', CAPTION),
    ]
