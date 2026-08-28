"""Secciones de marco: portada, índice, resultados globales, conclusiones."""

from datetime import datetime

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

from .. import charts, doctemplate, niveles, tables, text
from ..styles import BODY, CAPTION, H1, H2, SUBTITULO, TITULO, USABLE_W, imagen
from . import seccion


def _p(txt, estilo=BODY):
    return Paragraph(txt, estilo)


@seccion('portada', 'Portada', 100)
def portada(ctx, cfg):
    centrado = ParagraphStyle('centrado', parent=BODY, alignment=TA_CENTER)
    dist = ctx.distribucion

    partes = [
        Spacer(1, 4.5 * cm),
        _p('Evaluación de riesgo de desastre<br/>Sitio Patrimonio Mundial de Valparaíso', TITULO),
        Spacer(1, 0.6 * cm),
        _p(f'Amenaza: {ctx.nombre_amenaza}', SUBTITULO),
        Spacer(1, 1.4 * cm),
        _p(f'Generado el {datetime.now().strftime("%d-%m-%Y %H:%M")}', centrado),
    ]
    if dist:
        partes.append(_p(
            f'{dist["n"]} inmuebles evaluados de {ctx.total_inmuebles} catastrados · '
            f'índice medio {dist["media"]:.2f}'.replace('.', ','),
            centrado))
    return partes


@seccion('indice', 'Índice', 150)
def indice(ctx, cfg):
    if not cfg.incluir_indice:
        return []
    return [_p('Índice', H1), doctemplate.indice()]


@seccion('globales', 'Resultados globales', 300)
def globales(ctx, cfg):
    total = ctx.total_inmuebles
    amenazas_data = []
    promedios = []
    for _, a in ctx.amenazas.iterrows():
        aid = int(a['id'])
        filas = ctx.filas_nivel(aid)
        amenazas_data.append({
            'id': aid, 'nombre': a['nombre'], 'filas': filas,
            'dominante': niveles.dominante(filas),
        })
        promedios.append({'nombre': a['nombre'], 'promedio': ctx.promedio(aid),
                          'nivel': niveles.nivel_por_indice(ctx.promedio(aid))})
    promedios.sort(key=lambda p: p['promedio'], reverse=True)

    filas_actual = next(a['filas'] for a in amenazas_data if a['id'] == ctx.amenaza_id)
    no_eval = next(f['cantidad'] for f in filas_actual if f['nivel'] == niveles.NIVEL_NO_EVALUADO)

    partes = [
        _p('Resultados globales', H1),
        _p(text.intro_resultados_globales(list(ctx.amenazas['nombre'])), BODY),
        Spacer(1, 0.3 * cm),
        tables.resumen_amenazas(amenazas_data, total),
        _p(f'Tabla {ctx.tabla.siguiente()}. Resultados globales de la evaluación de riesgo.', CAPTION),
        _p(text.parrafo_evaluados(total, no_eval, ctx.nombre_amenaza), BODY),
        Spacer(1, 0.3 * cm),
        tables.rangos(text.DESCRIPTORES_NIVEL),
        _p(f'Tabla {ctx.tabla.siguiente()}. Rangos y descriptores del índice de riesgo.', CAPTION),
        _p(text.parrafo_promedios(promedios), BODY),
    ]

    if ctx.distribucion:
        series = {ctx.nombre_amenaza: ctx.indice()['indice_de_riesgo']}
        partes += [
            Spacer(1, 0.35 * cm),
            _p('Distribución del índice', H2),
            _p(text.parrafo_distribucion(ctx.distribucion, ctx.nombre_amenaza), BODY),
            tables.distribucion(ctx.distribucion, ctx.nombre_amenaza),
            _p(f'Tabla {ctx.tabla.siguiente()}. Estadística descriptiva del índice de riesgo.', CAPTION),
            imagen(charts.distribucion_indice(
                series, 'DISTRIBUCIÓN DEL ÍNDICE DE RIESGO', dpi=cfg.dpi_dona), USABLE_W * 0.94),
            _p(f'Figura {ctx.figura.siguiente()}. Distribución del índice sobre las bandas de nivel.',
               CAPTION),
        ]
    return partes


@seccion('conclusiones', 'Conclusiones', 1100)
def conclusiones(ctx, cfg):
    filas = ctx.filas_nivel()
    return [
        _p('Conclusiones y comentarios', H1),
        _p(text.conclusiones(filas, ctx.nombre_amenaza), BODY),
    ]
