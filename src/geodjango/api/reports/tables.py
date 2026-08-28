"""Tablas del informe."""

from reportlab.platypus import Table, TableStyle

from . import niveles, styles
from .styles import CELDA, GRIS, FONDO_CABECERA, USABLE_W


def _num(valor, decimales=2):
    return f'{valor:.{decimales}f}'.replace('.', ',')


def _base(estilos_extra=(), fontsize=7):
    return [
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), fontsize),
        ('GRID', (0, 0), (-1, -1), 0.5, GRIS),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), FONDO_CABECERA),
        *estilos_extra,
    ]


def evaluacion(filas, total, titulo='EVALUACIÓN GLOBAL', ancho=None):
    """Tabla ESCALA / Nº / % de una amenaza, indicador o sub-indicador."""
    ancho = ancho or USABLE_W * 0.42
    data = [[titulo, '', ''], ['ESCALA', 'Nº', '%']]
    estilos = [
        ('SPAN', (0, 0), (2, 0)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, GRIS),
        ('BACKGROUND', (0, 0), (-1, 1), FONDO_CABECERA),
    ]
    for i, f in enumerate(filas):
        r = i + 2
        data.append([f['nivel'].upper(), str(f['cantidad']), str(f['porcentaje'])])
        estilos += [
            ('BACKGROUND', (0, r), (0, r), styles.color_celda(f['nivel'])),
            ('TEXTCOLOR', (0, r), (0, r), styles.texto_contraste(f['nivel'])),
            ('FONTNAME', (0, r), (0, r), 'Helvetica-Bold'),
        ]
    rt = len(data)
    data.append(['TOTAL', str(total), '100'])
    estilos.append(('FONTNAME', (0, rt), (-1, rt), 'Helvetica-Bold'))

    col = ancho / 3
    t = Table(data, colWidths=[col * 1.5, col * 0.75, col * 0.75])
    t.setStyle(TableStyle(estilos))
    return t


def resumen_amenazas(amenazas_data, total):
    """Tabla 1: distribución por nivel, una columna doble por amenaza."""
    fila_amenaza = ['']
    fila_subhdr = ['ESCALA']
    for a in amenazas_data:
        fila_amenaza += [a['nombre'], '']
        fila_subhdr += ['Nº', '%']
    data = [fila_amenaza, fila_subhdr]

    for nivel in niveles.NIVELES:
        fila = [nivel.upper()]
        for a in amenazas_data:
            f = next((x for x in a['filas'] if x['nivel'] == nivel), {'cantidad': 0, 'porcentaje': 0})
            fila += [str(f['cantidad']), str(f['porcentaje'])]
        data.append(fila)

    fila_total = ['TOTAL']
    for _ in amenazas_data:
        fila_total += [str(total), '100']
    data.append(fila_total)

    fila_dom = ['NIVEL DOMINANTE']
    for a in amenazas_data:
        fila_dom += [a['dominante'].upper() if a['dominante'] else '—', '']
    data.append(fila_dom)

    n_dom = len(data) - 1
    estilos = [
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, GRIS),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 1), FONDO_CABECERA),
        ('FONTNAME', (0, len(niveles.NIVELES) + 2), (-1, len(niveles.NIVELES) + 2), 'Helvetica-Bold'),
        ('FONTNAME', (0, n_dom), (0, n_dom), 'Helvetica-Bold'),
    ]
    for idx in range(len(amenazas_data)):
        estilos.append(('SPAN', (1 + idx * 2, 0), (2 + idx * 2, 0)))
    for i, nivel in enumerate(niveles.NIVELES):
        r = i + 2
        estilos += [
            ('BACKGROUND', (0, r), (0, r), styles.color_celda(nivel)),
            ('TEXTCOLOR', (0, r), (0, r), styles.texto_contraste(nivel)),
            ('FONTNAME', (0, r), (0, r), 'Helvetica-Bold'),
        ]
    for idx, a in enumerate(amenazas_data):
        if a['dominante']:
            c0 = 1 + idx * 2
            estilos += [
                ('SPAN', (c0, n_dom), (c0 + 1, n_dom)),
                ('BACKGROUND', (c0, n_dom), (c0 + 1, n_dom), styles.color_celda(a['dominante'])),
                ('TEXTCOLOR', (c0, n_dom), (c0 + 1, n_dom), styles.texto_contraste(a['dominante'])),
                ('FONTNAME', (c0, n_dom), (c0 + 1, n_dom), 'Helvetica-Bold'),
            ]

    ncols = 1 + 2 * len(amenazas_data)
    col0 = USABLE_W * 0.22
    resto = (USABLE_W - col0) / (ncols - 1)
    t = Table(data, colWidths=[col0] + [resto] * (ncols - 1))
    t.setStyle(TableStyle(estilos))
    return t


def rangos(descriptores):
    """Tabla 2: rangos y descriptores, con los cortes derivados de los canónicos."""
    data = [['RANGO', 'NIVEL', 'DESCRIPCIÓN']]
    estilos = _base(fontsize=8)
    for i, nivel in enumerate(niveles.NIVELES_RIESGO):
        r = i + 1
        data.append([niveles.rango_texto(nivel), nivel.upper(),
                     styles.parrafo_celda(descriptores[nivel],
                                          styles.ParagraphStyle('d', parent=CELDA, fontSize=8, leading=10))])
        estilos += [
            ('BACKGROUND', (1, r), (1, r), styles.color_celda(nivel)),
            ('TEXTCOLOR', (1, r), (1, r), styles.texto_contraste(nivel)),
            ('FONTNAME', (1, r), (1, r), 'Helvetica-Bold'),
            ('ALIGN', (2, r), (2, r), 'LEFT'),
        ]
    t = Table(data, colWidths=[USABLE_W * 0.16, USABLE_W * 0.16, USABLE_W * 0.68])
    t.setStyle(TableStyle(estilos))
    return t


def distribucion(resumen, nombre_amenaza):
    """Estadística descriptiva del índice."""
    data = [
        ['INMUEBLES', 'MÍNIMO', 'Q1', 'MEDIANA', 'MEDIA', 'Q3', 'MÁXIMO', 'DESV. EST.'],
        [str(resumen['n']), _num(resumen['min']), _num(resumen['q1']), _num(resumen['mediana']),
         _num(resumen['media']), _num(resumen['q3']), _num(resumen['max']), _num(resumen['desv'])],
    ]
    t = Table(data, colWidths=[USABLE_W / 8] * 8)
    t.setStyle(TableStyle(_base(fontsize=7.5)))
    return t


def aporte(df, etiqueta='INDICADOR'):
    """Factores ordenados por aporte al índice: nombre, promedio, aporte %."""
    data = [['Nº', etiqueta, 'PROMEDIO', 'APORTE AL ÍNDICE']]
    estilos = _base(fontsize=7)
    estilos.append(('ALIGN', (1, 1), (1, -1), 'LEFT'))

    for i, (_, fila) in enumerate(df.iterrows(), start=1):
        data.append([
            str(i),
            styles.parrafo_celda(fila['factor_nombre'], CELDA),
            _num(fila['valor_medio']),
            f"{fila['aporte_pct']:.0f}%",
        ])

    anchos = [0.06, 0.58, 0.16, 0.20]
    t = Table(data, colWidths=[USABLE_W * a for a in anchos], repeatRows=1)
    t.setStyle(TableStyle(estilos))
    return t
