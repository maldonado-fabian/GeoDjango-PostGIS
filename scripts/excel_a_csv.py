#!/usr/bin/env python3
"""Convierte una base de datos de amenaza (.xlsx) al CSV que consume
`manage.py cargar_evaluaciones`.

Los cuatro Excel de amenazas (incendio, sismo, deslizamiento, graffiti) comparten
el mismo formato:

    fila 3   encabezado de grupo (el indicador) y celdas "TOTAL"
    fila 5   peso de cada sub-indicador; vacío en las columnas TOTAL
    fila 6   nombre de cada sub-indicador; en las columnas TOTAL, el peso del indicador
    fila 7+  una fila por inmueble; la columna F trae el rol SII

De ahí sale la regla que hace genérico este script: **una columna es sub-indicador
si y sólo si la fila 5 trae un peso numérico**. Las columnas TOTAL quedan fuera
solas, sin listas de índices escritas a mano.

Salida: `rol_sii,1,2,...,N`, donde el número de columna es el ORDEN del
sub-indicador dentro de la amenaza — no el id de `sub_indicadores`. Los ids
absolutos sólo servían mientras existía una única amenaza.

Sin dependencias: lee el .xlsx como zip + XML, así que no necesita openpyxl.

Uso:
    python3 scripts/excel_a_csv.py "media/bases de datos/sismo.xlsx" datos_sismo.csv
"""

import argparse
import csv
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

FILA_PESOS = 5
FILA_NOMBRES = 6
FILA_DATOS = 7
COL_ROL = 'F'


def _col(ref):
    """'AB12' -> 'AB'"""
    return re.sub(r'\d', '', ref)


def _indice(col):
    """'A' -> 1, 'AB' -> 28. Sirve para ordenar las columnas."""
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    return n


def leer_hoja(ruta):
    """{n_fila: {columna: valor}} de la primera hoja del libro."""
    z = zipfile.ZipFile(ruta)

    compartidas = []
    if 'xl/sharedStrings.xml' in z.namelist():
        raiz = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in raiz:
            compartidas.append(''.join(t.text or '' for t in si.iter(NS + 't')))

    hoja = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    filas = {}
    for fila in hoja.iter(NS + 'row'):
        celdas = {}
        for c in fila.iter(NS + 'c'):
            v = c.find(NS + 'v')
            if v is None:
                continue
            valor = v.text
            if c.get('t') == 's':
                valor = compartidas[int(valor)]
            celdas[_col(c.get('r'))] = valor
        filas[int(fila.get('r'))] = celdas
    return filas


def _numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def columnas_subindicadores(filas):
    """Columnas con peso en la fila 5, en orden de izquierda a derecha."""
    pesos = filas.get(FILA_PESOS, {})
    cols = [c for c, v in pesos.items() if _numero(v) is not None]
    return sorted(cols, key=_indice)


def convertir(entrada, salida):
    filas = leer_hoja(entrada)
    cols = columnas_subindicadores(filas)
    nombres = filas.get(FILA_NOMBRES, {})

    if not cols:
        sys.exit(f'No se detectó ninguna columna de sub-indicador en la fila {FILA_PESOS}.')

    print(f'{len(cols)} sub-indicadores detectados:')
    for i, c in enumerate(cols, 1):
        peso = filas[FILA_PESOS][c]
        print(f'  {i:>2}. [{c}] {(nombres.get(c) or "?").strip():<50} peso {peso}')

    escritas = sin_rol = 0
    with open(salida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['rol_sii'] + [str(i) for i in range(1, len(cols) + 1)])

        for n in sorted(filas):
            if n < FILA_DATOS:
                continue
            fila = filas[n]
            rol = (fila.get(COL_ROL) or '').strip()
            if not rol:
                sin_rol += 1
                continue
            # Los valores se copian tal cual: validarlos es tarea del comando de
            # carga, que es el único que conoce las clases definidas en la base.
            w.writerow([rol] + [(fila.get(c) or '').strip() for c in cols])
            escritas += 1

    print(f'\n{escritas} filas escritas en {salida}')
    if sin_rol:
        print(f'{sin_rol} filas omitidas por no tener rol SII en la columna {COL_ROL}')


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('excel', help='ruta del .xlsx de la amenaza')
    p.add_argument('csv', help='ruta del CSV de salida')
    args = p.parse_args()
    convertir(args.excel, args.csv)


if __name__ == '__main__':
    main()
