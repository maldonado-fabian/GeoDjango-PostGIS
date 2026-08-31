"""Tests del aporte por factor y del armado por secciones."""

import unittest

import pandas as pd
from django.test import SimpleTestCase

from api.reports import analytics, config, sections


AMENAZA_INCENDIO = 1
AMENAZA_SISMO = 3


def _contribuciones(filas):
    return pd.DataFrame(filas)


class AporteSinBase(SimpleTestCase):
    """El cálculo, sobre datos sintéticos: no necesita base de datos."""

    databases = []

    def _dataset(self, valores_por_sub, indicador_id=1, indicador_nombre='ind', peso_sub=0.5):
        filas = []
        for sub_id, valores in valores_por_sub.items():
            for inm, valor in enumerate(valores):
                filas.append({
                    'id_inmueble': inm,
                    'subindicador_id': sub_id,
                    'subindicador_nombre': f'sub{sub_id}',
                    'indicador_id': indicador_id,
                    'indicador_nombre': indicador_nombre,
                    'valor': float(valor),
                    'peso_sub': peso_sub,
                    'peso_ind': 1.0,
                    'contribucion': float(valor) * peso_sub,
                })
        return _contribuciones(filas)

    def test_ordena_de_mayor_a_menor_aporte(self):
        df = analytics.aporte_por_factor(self._dataset({
            1: [1, 1, 1, 1],   # aporte bajo
            2: [4, 4, 4, 4],   # aporte alto
        }), nivel=analytics.NIVEL_SUBINDICADOR)
        self.assertEqual(df.iloc[0]['factor_nombre'], 'sub2')
        self.assertGreater(df.iloc[0]['aporte_pct'], df.iloc[1]['aporte_pct'])

    def test_dataset_vacio_no_revienta(self):
        df = analytics.aporte_por_factor(_contribuciones([]))
        self.assertTrue(df.empty)

    def test_nivel_indicador_agrega_sus_subindicadores(self):
        """El aporte del indicador es la suma del de sus dos sub-indicadores."""
        datos = self._dataset({1: [2, 2, 2, 2], 2: [4, 4, 4, 4]}, peso_sub=0.5)
        por_sub = analytics.aporte_por_factor(datos, nivel=analytics.NIVEL_SUBINDICADOR)
        por_ind = analytics.aporte_por_factor(datos, nivel=analytics.NIVEL_INDICADOR)

        self.assertEqual(len(por_ind), 1)
        self.assertAlmostEqual(por_ind.iloc[0]['aporte_pct'], por_sub['aporte_pct'].sum(), places=4)


def _base_disponible():
    try:
        from api.reports import queries
        queries.total_inmuebles()
        return True
    except Exception:
        return False


requiere_db = unittest.skipUnless(_base_disponible(), 'Base de datos no disponible')


@requiere_db
class AporteSobreDatosReales(SimpleTestCase):

    databases = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from api.reports.context import ReportContext
        cls.ctx = ReportContext(config.ReportConfig(amenaza_id=AMENAZA_INCENDIO))

    def test_aportes_suman_aproximadamente_cien(self):
        """El aporte es una descomposición del índice: debe cerrar en 100%."""
        self.assertAlmostEqual(self.ctx.aporte_indicadores['aporte_pct'].sum(), 100.0, places=0)

    def test_un_indicador_por_fila(self):
        self.assertEqual(len(self.ctx.aporte_indicadores), len(self.ctx.indicadores))

    def test_el_puntaje_queda_en_la_escala_1_4(self):
        valores = self.ctx.aporte_indicadores['valor_medio']
        self.assertGreaterEqual(valores.min(), 1.0)
        self.assertLessEqual(valores.max(), 4.0)


class RegistroDeSecciones(SimpleTestCase):

    databases = []

    def test_los_ordenes_son_unicos(self):
        ordenes = [s.orden for s in sections.REGISTRY.values()]
        self.assertEqual(len(ordenes), len(set(ordenes)), 'Hay secciones con el mismo orden')

    def test_catalogo_no_esta_vacio(self):
        self.assertGreater(len(sections.REGISTRY), 0)

    def test_seccion_desconocida_es_error(self):
        cfg = config.ReportConfig(amenaza_id=1, secciones=('no_existe',))
        with self.assertRaises(ValueError):
            sections.secciones_para(cfg)

    def test_excluir_quita_una_seccion(self):
        cfg = config.ReportConfig(amenaza_id=1, excluir=('conclusiones',))
        ids = {s.id for s in sections.secciones_para(cfg)}
        self.assertNotIn('conclusiones', ids)


@requiere_db
class GeneracionDelInforme(SimpleTestCase):

    databases = []

    def test_genera_un_pdf_para_cada_amenaza(self):
        from api.reports import pdf
        for amenaza_id in (AMENAZA_INCENDIO, AMENAZA_SISMO):
            with self.subTest(amenaza=amenaza_id):
                datos = pdf.generar(config.ReportConfig(amenaza_id=amenaza_id))
                self.assertTrue(datos.startswith(b'%PDF'))

    def test_una_sola_seccion_produce_un_documento_corto(self):
        """La lista blanca permite revisar una sección aislada."""
        import re
        from api.reports import pdf

        datos = pdf.generar(config.ReportConfig(
            amenaza_id=AMENAZA_SISMO, secciones=('portada',), incluir_indice=False))
        paginas = max(int(m) for m in re.findall(rb'/Count (\d+)', datos))
        self.assertLessEqual(paginas, 2)
