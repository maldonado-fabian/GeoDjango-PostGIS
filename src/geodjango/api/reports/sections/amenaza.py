"""Secciones de la amenaza evaluada: resultado global, indicadores, sub-indicadores."""

from reportlab.platypus import PageBreak, Paragraph

from .. import charts, niveles, tables, text
from ..config import MODO_COMPLETO
from ..styles import (BODY, CAPTION, H1, H2,
                      figura_compuesta, gdf_coloreado, grid_donas)
from . import seccion


def _p(txt, estilo=BODY):
    return Paragraph(txt, estilo)


#: Largo máximo de una etiqueta de clase en la leyenda de un mapa. Por encima
#: de esto el recuadro se come la figura.
MAX_ETIQUETA = 34


def etiqueta_clase(etiquetas, subindicador_id, valor):
    """'4 · Entramado de madera' en vez de '4'."""
    nombre = (etiquetas.get(int(subindicador_id)) or {}).get(int(valor))
    if not nombre:
        return str(valor)
    if len(nombre) > MAX_ETIQUETA:
        nombre = nombre[:MAX_ETIQUETA - 1].rstrip() + '…'
    return f'{valor} · {nombre}'


@seccion('amenaza_detalle', 'Resultado de la amenaza', 400)
def amenaza_detalle(ctx, cfg):
    total = ctx.total_inmuebles
    filas = ctx.filas_nivel()
    idx = ctx.indice().copy()
    idx['nivel'] = idx['indice_de_riesgo'].map(niveles.nivel_por_indice)

    gdf = gdf_coloreado(ctx.geo, idx[['id_inmueble', 'nivel']])
    # Incluye "No evaluado": el mapa pinta de gris esos inmuebles.
    leyenda = [(n, niveles.color(n)) for n in niveles.NIVELES]

    mapa_png = charts.mapa(gdf, ctx.nombre_amenaza, leyenda,
                           etiqueta_leyenda=ctx.nombre_amenaza.upper(),
                           dpi=cfg.dpi_mapa, basemap=cfg.basemap)
    dona_png = charts.donut(filas, 'RESULTADO GLOBAL Nº; % DE EDIFICIOS', dpi=cfg.dpi_dona)

    return [
        _p(f'Detalle de la amenaza: {ctx.nombre_amenaza}', H1),
        _p(text.detalle_amenaza_intro(ctx.nombre_amenaza, list(ctx.indicadores['nombre'])), BODY),
        _p(f'Resultados globales de la amenaza {ctx.nombre_amenaza.lower()}', H2),
        _p(text.parrafo_resultados_amenaza(filas, total), BODY),
        figura_compuesta(mapa_png, tables.evaluacion(filas, total), dona_png),
        _p(f'Figura {ctx.figura.siguiente()}. Resultado global de la amenaza '
           f'{ctx.nombre_amenaza.lower()}.', CAPTION),
    ]


@seccion('indicadores', 'Indicadores primarios', 900)
def indicadores(ctx, cfg):
    total = ctx.total_inmuebles
    donas = []
    for _, g in ctx.indicador_scores.groupby('indicador_id', sort=True):
        nombre = g['indicador_nombre'].iloc[0]
        nivs = [niveles.nivel_por_indice(v) for v in g['score']]
        donas.append(charts.donut(niveles.conteo(nivs, total),
                                  f'{nombre.upper()} Nº; % DE EDIFICIOS', dpi=cfg.dpi_dona))
    return [
        _p('Incidencia de los indicadores primarios', H2),
        _p(text.parrafo_indicadores_primarios(), BODY),
        grid_donas(donas),
        _p(f'Figura {ctx.figura.siguiente()}. Resultados de los indicadores primarios.', CAPTION),
    ]


@seccion('subindicadores', 'Indicadores secundarios', 1000)
def subindicadores(ctx, cfg):
    """Tabla comparativa en modo ejecutivo; una página por sub-indicador en completo.

    Las veinte páginas por sub-indicador eran el grueso del informe anterior.
    En la versión ejecutiva se condensan en la tabla del diagnóstico, y aquí
    quedan sólo si el lector pidió el detalle.
    """
    if cfg.modo != MODO_COMPLETO:
        return []

    total = ctx.total_inmuebles
    partes = [
        _p('Incidencia de los indicadores secundarios', H2),
        _p(text.parrafo_indicadores_secundarios(), BODY),
    ]

    for sub_id, g in ctx.subindicador_valores.groupby('subindicador_id', sort=True):
        nombre = g['subindicador_nombre'].iloc[0]
        nivs = [niveles.nivel_por_valor_crudo(v) for v in g['valor']]
        filas = niveles.conteo(nivs, total)
        promedio = float(g['valor'].mean()) if len(g) else 0.0

        gv = g[['id_inmueble', 'valor']].copy()
        gv['nivel'] = gv['valor'].map(niveles.nivel_por_valor_crudo)
        gdf = gdf_coloreado(ctx.geo, gv[['id_inmueble', 'nivel']])

        leyenda = [
            (etiqueta_clase(ctx.etiquetas_clase, sub_id, v),
             niveles.color(niveles.nivel_por_valor_crudo(v)))
            for v in (1, 2, 3, 4)
        ]
        mapa_png = charts.mapa(gdf, nombre, leyenda, etiqueta_leyenda=nombre.upper(),
                               dpi=cfg.dpi_mapa, basemap=cfg.basemap)
        dona_png = charts.donut(filas, f'{nombre.upper()} Nº; % DE EDIFICIOS', dpi=cfg.dpi_dona)

        partes += [
            PageBreak(),
            _p(f'Indicador secundario: {nombre}', H2),
            _p(text.parrafo_subindicador(nombre, promedio,
                                         niveles.nivel_por_indice(promedio)), BODY),
            figura_compuesta(mapa_png, tables.evaluacion(filas, total, nombre.upper()), dona_png),
            _p(f'Figura {ctx.figura.siguiente()}. Resultado del indicador secundario '
               f'«{nombre}».', CAPTION),
        ]
    return partes
