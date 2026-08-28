"""Paridad de los umbrales de nivel de riesgo entre las tres implementaciones.

La plataforma clasifica el índice de riesgo (escala 1–4) en cuatro niveles, pero
hoy lo hace en tres lugares que NO coinciden:

- `api/reports/niveles.py`  -> cortes por cota inferior:  >= 3.26 / >= 2.51 / >= 1.76
- `api/views.py`            -> cortes por cota superior:  <= 1.75 / <= 2.5  / <= 3.25
  (en `sql_indice_por_inmueble` como CASE SQL y en `CrearKMLDetalleView` en Python)
- `src/mapa/main.js`        -> coincide con niveles.py

Las dos primeras dejan huecos de 0,01 en cada frontera (1,75–1,76 · 2,50–2,51 ·
3,25–3,26). Un índice que cae dentro del hueco se clasifica distinto según quién
lo mire: 2,505 es "Medio" en el PDF y "Alto" en el KML del mismo dato.

Estos tests documentan esa divergencia. `test_paridad_en_frontera` FALLA a
propósito antes de la Fase 1 (consolidación en `api/riesgo.py`); es la red de
seguridad que verifica que la consolidación efectivamente arregla el problema.
"""

import re
import unittest
from pathlib import Path

from django.test import SimpleTestCase

from api import riesgo
from api.reports import niveles


#: Valores límite: los tres huecos históricos, sus bordes, y puntos interiores.
VALORES_FRONTERA = [
    1.00, 1.50,
    1.75, 1.755, 1.76,      # antiguo hueco Bajo/Medio
    2.00, 2.49,
    2.50, 2.505, 2.51,      # antiguo hueco Medio/Alto
    2.90, 3.24,
    3.25, 3.255, 3.26,      # antiguo hueco Alto/Muy Alto
    3.50, 4.00,
]


class ParidadPythonSQL(SimpleTestCase):
    """El clasificador en Python y el CASE de SQL deben coincidir.

    Se ejecuta el SQL que `riesgo.case_sql()` genera realmente contra Postgres,
    en vez de replicar su lógica aquí: una réplica en el test envejece con el
    código y deja de detectar nada.
    """

    databases = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            from api.reports.queries import _engine
            cls.engine = _engine()
            with cls.engine.connect():
                pass
            cls.disponible = True
        except Exception:
            cls.disponible = False

    def test_case_sql_coincide_con_python(self):
        if not self.disponible:
            raise unittest.SkipTest('Base de datos no disponible')

        from sqlalchemy import text

        # Una sola consulta con todos los valores: VALUES(...) alimenta el CASE.
        filas = ', '.join(f'({v})' for v in VALORES_FRONTERA)
        sql = f"""
            SELECT v.indice, {riesgo.case_sql('v.indice')} AS color
            FROM (VALUES {filas}) AS v(indice)
        """
        with self.engine.connect() as con:
            resultado = con.execute(text(sql)).fetchall()

        divergencias = [
            (float(indice), riesgo.nivel_por_indice(indice).color, color_sql)
            for indice, color_sql in resultado
            if riesgo.nivel_por_indice(indice).color != color_sql
        ]
        self.assertEqual(
            divergencias, [],
            'El clasificador de Python y el CASE de SQL difieren. '
            f'(índice, color en Python, color en SQL): {divergencias}'
        )


class ParidadAdaptador(SimpleTestCase):
    """El adaptador `reports/niveles.py` no debe alterar la clasificación canónica."""

    databases = []

    def test_adaptador_coincide_con_canonico(self):
        divergencias = [
            (v, niveles.nivel_por_indice(v), riesgo.nivel_por_indice(v).label)
            for v in VALORES_FRONTERA
            if niveles.nivel_por_indice(v) != riesgo.nivel_por_indice(v).label
        ]
        self.assertEqual(divergencias, [], f'El adaptador diverge del canónico: {divergencias}')

    def test_rangos_derivados_de_los_cortes(self):
        """Los textos de rango se derivan; antes eran literales en la Tabla 2."""
        self.assertEqual(niveles.rango_texto(niveles.NIVEL_BAJO), '1,00 – 1,75')
        self.assertEqual(niveles.rango_texto(niveles.NIVEL_MEDIO), '1,76 – 2,50')
        self.assertEqual(niveles.rango_texto(niveles.NIVEL_ALTO), '2,51 – 3,25')
        self.assertEqual(niveles.rango_texto(niveles.NIVEL_MUY_ALTO), '3,26 – 4,00')


class UmbralesCanonicos(SimpleTestCase):

    databases = []

    def test_cortes_declarados(self):
        """Los cortes de niveles.py son los canónicos y no cambiaron por accidente."""
        self.assertEqual(niveles.nivel_por_indice(3.26), niveles.NIVEL_MUY_ALTO)
        self.assertEqual(niveles.nivel_por_indice(3.25), niveles.NIVEL_ALTO)
        self.assertEqual(niveles.nivel_por_indice(2.51), niveles.NIVEL_ALTO)
        self.assertEqual(niveles.nivel_por_indice(2.50), niveles.NIVEL_MEDIO)
        self.assertEqual(niveles.nivel_por_indice(1.76), niveles.NIVEL_MEDIO)
        self.assertEqual(niveles.nivel_por_indice(1.75), niveles.NIVEL_BAJO)

    def test_valores_no_numericos_son_no_evaluado(self):
        for v in (None, float('nan'), 'sin dato', ''):
            self.assertEqual(niveles.nivel_por_indice(v), niveles.NIVEL_NO_EVALUADO, f'valor {v!r}')


class ParidadUmbralesFrontend(SimpleTestCase):
    """El frontend replica los cortes en JS; no puede importarlos del backend.

    En vez de acoplarlos en runtime (un fetch al arrancar el mapa), se verifica
    la paridad aquí: barato, sin acoplamiento, y detecta la deriva igual.
    """

    MAIN_JS = Path(__file__).resolve().parents[3] / 'mapa' / 'main.js'

    def _niveles_de_main_js(self):
        """Extrae el array NIVELES de main.js -> [(min, fill), ...] descendente."""
        fuente = self.MAIN_JS.read_text(encoding='utf-8')
        bloque = re.search(r'const NIVELES\s*=\s*\[(.*?)\];', fuente, re.S)
        self.assertIsNotNone(bloque, f'No se encontró `const NIVELES` en {self.MAIN_JS}')

        encontrados = []
        for linea in bloque.group(1).splitlines():
            m_fill = re.search(r"fill:\s*'(#[0-9a-fA-F]{6})'", linea)
            m_min = re.search(r'min:\s*(-?[\d.]+|-Infinity)', linea)
            if m_fill and m_min:
                crudo = m_min.group(1)
                encontrados.append((float('-inf') if crudo == '-Infinity' else float(crudo),
                                    m_fill.group(1).lower()))
        return encontrados

    def test_main_js_existe(self):
        self.assertTrue(self.MAIN_JS.is_file(), f'No existe {self.MAIN_JS}')

    def test_cortes_y_colores_coinciden(self):
        js = self._niveles_de_main_js()
        self.assertEqual(len(js), 4, f'Se esperaban 4 niveles en main.js, se leyeron {len(js)}')

        esperado = [
            (3.26, niveles.COLORES[niveles.NIVEL_MUY_ALTO].lower()),
            (2.51, niveles.COLORES[niveles.NIVEL_ALTO].lower()),
            (1.76, niveles.COLORES[niveles.NIVEL_MEDIO].lower()),
            (float('-inf'), niveles.COLORES[niveles.NIVEL_BAJO].lower()),
        ]
        self.assertEqual(
            js, esperado,
            'Los cortes o colores de src/mapa/main.js divergen de api/reports/niveles.py. '
            'El mapa y el PDF mostrarían niveles distintos para el mismo inmueble.'
        )
