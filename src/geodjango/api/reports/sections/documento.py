"""Secciones de marco: portada, índice, resumen ejecutivo, globales, cierre."""

from datetime import datetime

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

from .. import charts, doctemplate, niveles, tables, text
from ..config import MODO_COMPLETO, MODO_EJECUTIVO
from ..styles import BODY, CAPTION, H1, H2, NOTA, SUBTITULO, TITULO
from . import seccion


def _p(txt, estilo=BODY):
    return Paragraph(txt, estilo)


@seccion('portada', 'Portada', 100)
def portada(ctx, cfg):
    centrado = ParagraphStyle('centrado', parent=BODY, alignment=TA_CENTER)
    modo = 'Versión ejecutiva' if cfg.modo == MODO_EJECUTIVO else 'Versión completa'
    dist = ctx.distribucion

    partes = [
        Spacer(1, 4.5 * cm),
        _p('Evaluación de riesgo de desastre<br/>Sitio Patrimonio Mundial de Valparaíso', TITULO),
        Spacer(1, 0.6 * cm),
        _p(f'Amenaza: {ctx.nombre_amenaza}', SUBTITULO),
        Spacer(1, 1.4 * cm),
        _p(f'{modo} · generado el {datetime.now().strftime("%d-%m-%Y %H:%M")}', centrado),
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


@seccion('resumen_ejecutivo', 'Resumen ejecutivo', 200)
def resumen_ejecutivo(ctx, cfg):
    """Hallazgos con su número y la decisión que implica cada uno."""
    partes = [_p('Resumen ejecutivo', H1),
              _p(text.intro_resumen_ejecutivo(ctx.nombre_amenaza), BODY),
              Spacer(1, 0.3 * cm)]

    for i, hallazgo in enumerate(text.hallazgos(ctx), start=1):
        partes.append(_p(f'<b>{i}. {hallazgo["titulo"]}</b>', BODY))
        partes.append(_p(hallazgo['cuerpo'], BODY))
        partes.append(_p(f'<b>Implicancia:</b> {hallazgo["implicancia"]}', NOTA))
        partes.append(Spacer(1, 0.25 * cm))
    return partes


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
        otra = ctx.amenaza_comparacion
        if otra is not None:
            series[otra['nombre']] = ctx.indice(int(otra['id']))['indice_de_riesgo']

        partes += [
            Spacer(1, 0.35 * cm),
            _p('Distribución del índice', H2),
            _p(text.parrafo_distribucion(ctx.distribucion, ctx.nombre_amenaza), BODY),
            tables.distribucion(ctx.distribucion, ctx.nombre_amenaza),
            _p(f'Tabla {ctx.tabla.siguiente()}. Estadística descriptiva del índice de riesgo.', CAPTION),
            charts_imagen(charts.distribucion_indice(
                series, 'DISTRIBUCIÓN DEL ÍNDICE DE RIESGO', dpi=cfg.dpi_dona)),
            _p(f'Figura {ctx.figura.siguiente()}. Distribución del índice sobre las bandas de nivel.',
               CAPTION),
        ]
    return partes


def charts_imagen(png):
    from ..styles import USABLE_W, imagen
    return imagen(png, USABLE_W * 0.94)


@seccion('metodologia', 'Metodología', 350, modos=(MODO_COMPLETO,))
def metodologia(ctx, cfg):
    faltantes = text.cobertura_faltante(ctx)
    partes = [
        _p('Metodología', H1),
        _p(text.parrafo_metodologia(ctx), BODY),
        Spacer(1, 0.3 * cm),
        _p('Ponderadores', H2),
        _p(text.parrafo_pesos(), BODY),
        tables.pesos(ctx.indicadores, ctx.contribuciones),
        _p(f'Tabla {ctx.tabla.siguiente()}. Pesos de indicadores y sub-indicadores.', CAPTION),
        Spacer(1, 0.3 * cm),
        _p('Cobertura de la evaluación', H2),
        _p(faltantes, BODY),
    ]
    return partes


@seccion('conclusiones', 'Conclusiones', 1100)
def conclusiones(ctx, cfg):
    filas = ctx.filas_nivel()
    return [
        _p('Conclusiones y acciones recomendadas', H1),
        _p(text.conclusiones(filas, ctx.nombre_amenaza), BODY),
        Spacer(1, 0.3 * cm),
        _p('Acciones priorizadas', H2),
        *[_p(f'<b>{i}.</b> {accion}', BODY)
          for i, accion in enumerate(text.acciones(ctx), start=1)],
    ]
