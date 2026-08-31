"""Secciones de marco: portada, índice, resultados globales, conclusiones."""

from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, Spacer

from .. import charts, doctemplate, niveles, tables, text
from ..styles import BODY, CAPTION, H1, H2, SUBTITULO, TITULO, USABLE_W, imagen
from . import seccion


_MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
          'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre')


def _fecha_larga(dt):
    """'29 de agosto de 2026'. `strftime('%B')` depende del locale del
    contenedor, así que los nombres de mes se resuelven a mano."""
    return f'{dt.day} de {_MESES[dt.month - 1]} de {dt.year}'


def _p(txt, estilo=BODY):
    return Paragraph(txt, estilo)


def _regla(color='#999999', grosor=0.6):
    return HRFlowable(width='100%', thickness=grosor, color=colors.HexColor(color),
                      spaceBefore=0, spaceAfter=0)


@seccion('portada', 'Portada', 100)
def portada(ctx, cfg):
    centrado = ParagraphStyle('centrado', parent=BODY, alignment=TA_CENTER, spaceAfter=0)
    institucional = ParagraphStyle('institucional', parent=BODY, alignment=TA_CENTER,
                                   fontName='Times-Bold', fontSize=10, spaceAfter=0,
                                   textColor=colors.HexColor('#5b5f60'))
    dist = ctx.distribucion

    partes = [
        Spacer(1, 3.6 * cm),
        _p('Unidad de Gestión de Riesgo', institucional),
        Spacer(1, 0.3 * cm),
        _regla(),
        Spacer(1, 0.7 * cm),
        _p('Evaluación de riesgo de desastre<br/>Sitio Patrimonio Mundial de Valparaíso', TITULO),
        Spacer(1, 0.6 * cm),
        _p(f'Amenaza evaluada: {ctx.nombre_amenaza}', SUBTITULO),
        Spacer(1, 1.6 * cm),
        _p(f'Informe generado el {_fecha_larga(datetime.now())}, {datetime.now().strftime("%H:%M")} hrs.',
           centrado),
    ]
    if dist:
        partes.append(Spacer(1, 0.15 * cm))
        partes.append(_p(
            f'{dist["n"]} inmuebles evaluados de {ctx.total_inmuebles} catastrados · '
            f'índice medio {dist["media"]:.2f}'.replace('.', ','),
            centrado))
    return partes


@seccion('indice', 'Índice', 150)
def indice(ctx, cfg):
    if not cfg.incluir_indice:
        return []
    # El índice no lleva numeración de sección: es la lista de las que sí la
    # llevan, y numerarlo a sí mismo confundiría al lector.
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
        _p(ctx.titulos.h1('Resultados globales'), H1),
        _p(text.intro_resultados_globales(list(ctx.amenazas['nombre'])), BODY),
        Spacer(1, 0.3 * cm),
        tables.resumen_amenazas(amenazas_data, total),
        _p(f'Tabla {ctx.tabla.siguiente()}. Resultados globales de la evaluación de riesgo.', CAPTION),
        _p(text.parrafo_evaluados(total, no_eval, ctx.nombre_amenaza), BODY),
        Spacer(1, 0.3 * cm),
        _p(text.intro_rangos(), BODY),
        tables.rangos(text.DESCRIPTORES_NIVEL),
        _p(f'Tabla {ctx.tabla.siguiente()}. Rangos y descriptores del índice de riesgo.', CAPTION),
        _p(text.parrafo_promedios(promedios), BODY),
    ]

    if ctx.distribucion:
        series = {ctx.nombre_amenaza: ctx.indice()['indice_de_riesgo']}
        partes += [
            Spacer(1, 0.35 * cm),
            _p(ctx.titulos.h2('Distribución del índice'), H2),
            _p(text.parrafo_distribucion(ctx.distribucion, ctx.nombre_amenaza), BODY),
            tables.distribucion(ctx.distribucion, ctx.nombre_amenaza),
            _p(f'Tabla {ctx.tabla.siguiente()}. Estadística descriptiva del índice de riesgo.', CAPTION),
            imagen(charts.distribucion_indice(
                series, 'DISTRIBUCIÓN DEL ÍNDICE DE RIESGO', dpi=cfg.dpi_dona), USABLE_W * 0.94),
            _p(f'Figura {ctx.figura.siguiente()}. Distribución del índice sobre las bandas de nivel.',
               CAPTION),
        ]
    return partes


#: Sub-indicadores mostrados en la tabla y el gráfico de puntos críticos.
_TOP_CRITICOS = 8


@seccion('conclusiones', 'Conclusiones y recomendaciones', 1100)
def conclusiones(ctx, cfg):
    filas = ctx.filas_nivel()

    partes = [
        _p(ctx.titulos.h1('Conclusiones y recomendaciones'), H1),
        _p(ctx.titulos.h2('Síntesis general'), H2),
        _p(text.conclusiones(filas, ctx.nombre_amenaza), BODY),
    ]

    top_ind = ctx.aporte_indicadores
    top_sub = ctx.aporte_subindicadores
    if not top_sub.empty:
        top_sub_n = top_sub.head(_TOP_CRITICOS)
        partes += [
            Spacer(1, 0.3 * cm),
            _p(ctx.titulos.h2('Puntos críticos'), H2),
            _p(text.intro_puntos_criticos(ctx.nombre_amenaza), BODY),
            _p(text.parrafo_puntos_criticos(top_ind, top_sub), BODY),
            Spacer(1, 0.2 * cm),
            imagen(charts.barras_aporte(
                top_sub_n, 'INDICADORES SECUNDARIOS DE MAYOR APORTE AL ÍNDICE', dpi=cfg.dpi_dona),
                USABLE_W * 0.9),
            _p(f'Figura {ctx.figura.siguiente()}. Los {len(top_sub_n)} indicadores secundarios '
               f'que más aportan al índice de riesgo, de un total de {len(top_sub)}.', CAPTION),
            tables.aporte(top_sub_n, etiqueta='INDICADOR SECUNDARIO'),
            _p(f'Tabla {ctx.tabla.siguiente()}. Detalle de los indicadores secundarios críticos.',
               CAPTION),
            Spacer(1, 0.3 * cm),
            _p(ctx.titulos.h2('Recomendaciones'), H2),
            *[_p(f'{i}. {r}', BODY)
              for i, r in enumerate(text.recomendaciones(top_sub, ctx.distribucion, ctx.total_inmuebles), 1)],
        ]

    return partes
