"""Secciones de la amenaza evaluada: resultado global, indicadores, sub-indicadores.

Los indicadores primarios y secundarios se presentan con el mismo bloque:
mapa · tabla resumen · dona, en una sola fila, de modo que caben dos por página.
Antes los primarios sólo tenían dona -sin mapa- y cada secundario ocupaba una
página entera.
"""

from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

from .. import charts, niveles, tables, text
from ..styles import (BODY, CAPTION, H1, H2, USABLE_W, ancho_tabla_compacta,
                      figura_compacta, figura_compuesta, gdf_coloreado, imagen)
from . import seccion


def _p(txt, estilo=BODY):
    return Paragraph(txt, estilo)


def _fig(png, ancho=0.94):
    return imagen(png, USABLE_W * ancho)


def _descripciones_indicadores(ctx):
    """{nombre_indicador: descripcion}, para enriquecer cada bloque."""
    return dict(zip(ctx.indicadores['nombre'], ctx.indicadores['descripcion']))


#: Largo máximo de una etiqueta de clase en la leyenda de un mapa. Por encima
#: de esto el recuadro se come la figura.
MAX_ETIQUETA = 28


def etiqueta_clase(etiquetas, subindicador_id, valor):
    """'4 · Entramado de madera' en vez de '4'."""
    nombre = (etiquetas.get(int(subindicador_id)) or {}).get(int(valor))
    if not nombre:
        return str(valor)
    if len(nombre) > MAX_ETIQUETA:
        nombre = nombre[:MAX_ETIQUETA - 1].rstrip() + '…'
    return f'{valor} · {nombre}'


def _bloque(ctx, cfg, *, titulo, gdf, leyenda, filas, etiqueta_leyenda, pie, texto=None):
    """Bloque compacto de media página: mapa · tabla · dona, con párrafo de detalle."""
    mapa_png = charts.mapa(gdf, titulo, leyenda, etiqueta_leyenda=etiqueta_leyenda,
                           dpi=cfg.dpi_mapa, basemap=cfg.basemap,
                           compacto=True, sin_titulo=True)
    dona_png = charts.donut(filas, titulo, dpi=cfg.dpi_dona,
                            compacto=True, sin_titulo=True)
    tabla = tables.evaluacion(filas, ctx.total_inmuebles, titulo='DISTRIBUCIÓN',
                              ancho=ancho_tabla_compacta())
    return figura_compacta(titulo, mapa_png, tabla, dona_png, pie, texto=texto)


@seccion('amenaza_detalle', 'Resultado de la amenaza', 400)
def amenaza_detalle(ctx, cfg):
    """Resultado global, a página completa: es la figura de referencia."""
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
        _p(ctx.titulos.h1(f'Detalle de la amenaza: {ctx.nombre_amenaza}'), H1),
        _p(text.detalle_amenaza_intro(ctx.nombre_amenaza, list(ctx.indicadores['nombre'])), BODY),
        _p(ctx.titulos.h2(f'Resultados globales de la amenaza {ctx.nombre_amenaza.lower()}'), H2),
        _p(text.parrafo_resultados_amenaza(filas, total), BODY),
        figura_compuesta(mapa_png, tables.evaluacion(filas, total), dona_png),
        _p(f'Figura {ctx.figura.siguiente()}. Resultado global de la amenaza '
           f'{ctx.nombre_amenaza.lower()}.', CAPTION),
    ]


@seccion('indicadores', 'Indicadores primarios', 900)
def indicadores(ctx, cfg):
    """Qué factores explican el riesgo, y luego un bloque por indicador con mapa."""
    total = ctx.total_inmuebles
    partes = [_p(ctx.titulos.h1('Indicadores primarios'), H1)]

    aporte = ctx.aporte_indicadores
    if not aporte.empty:
        top = aporte.iloc[0]
        partes += [
            _p(ctx.titulos.h2('Qué factores explican el riesgo'), H2),
            _p(text.intro_factores(top['factor_nombre'], top['aporte_pct']), BODY),
            Spacer(1, 0.2 * cm),
            _fig(charts.barras_aporte(aporte, 'APORTE DE CADA INDICADOR AL ÍNDICE', dpi=cfg.dpi_dona)),
            _p(f'Figura {ctx.figura.siguiente()}. Aporte de cada indicador primario al índice '
               f'de riesgo.', CAPTION),
            tables.aporte(aporte, etiqueta='INDICADOR'),
            _p(f'Tabla {ctx.tabla.siguiente()}. Detalle ordenado por aporte al índice.', CAPTION),
            Spacer(1, 0.3 * cm),
        ]

    partes += [
        _p(ctx.titulos.h2('Espacialización de los indicadores primarios'), H2),
        _p(text.parrafo_indicadores_primarios(), BODY),
    ]

    leyenda = [(n, niveles.color(n)) for n in niveles.NIVELES]
    descripciones = _descripciones_indicadores(ctx)

    for _, g in ctx.indicador_scores.groupby('indicador_id', sort=True):
        nombre = g['indicador_nombre'].iloc[0]
        nivs = [niveles.nivel_por_indice(v) for v in g['score']]
        filas = niveles.conteo(nivs, total)

        gv = g[['id_inmueble', 'score']].copy()
        gv['nivel'] = gv['score'].map(niveles.nivel_por_indice)
        gdf = gdf_coloreado(ctx.geo, gv[['id_inmueble', 'nivel']])

        promedio = float(g['score'].mean()) if len(g) else 0.0
        partes.append(_bloque(
            ctx, cfg, titulo=nombre, gdf=gdf, leyenda=leyenda, filas=filas,
            etiqueta_leyenda='NIVEL',
            texto=text.parrafo_indicador_detalle(nombre, descripciones.get(nombre), filas, promedio),
            pie=(f'Figura {ctx.figura.siguiente()}. Indicador primario «{nombre}» · '
                 f'promedio {promedio:.2f}'.replace('.', ',')),
        ))
    return partes


@seccion('subindicadores', 'Indicadores secundarios', 1000)
def subindicadores(ctx, cfg):
    """Un bloque por sub-indicador, dos por página.

    Antes cada uno ocupaba una página entera: veinte páginas de las veintiséis
    del informe original.
    """
    total = ctx.total_inmuebles
    partes = [
        _p(ctx.titulos.h1('Indicadores secundarios'), H1),
        _p(text.parrafo_indicadores_secundarios(), BODY),
    ]

    for sub_id, g in ctx.subindicador_valores.groupby('subindicador_id', sort=True):
        nombre = g['subindicador_nombre'].iloc[0]
        descripcion = g['subindicador_descripcion'].iloc[0]
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
        partes.append(_bloque(
            ctx, cfg, titulo=nombre, gdf=gdf, leyenda=leyenda, filas=filas,
            etiqueta_leyenda='CLASE',
            texto=text.parrafo_subindicador_detalle(nombre, descripcion, filas, promedio),
            pie=(f'Figura {ctx.figura.siguiente()}. Indicador secundario «{nombre}» · '
                 f'promedio {promedio:.2f}'.replace('.', ',')),
        ))
    return partes
