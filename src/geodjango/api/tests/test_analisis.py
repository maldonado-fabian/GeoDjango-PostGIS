"""Tests del diagnóstico de factores y del armado por secciones."""

import unittest

import pandas as pd
from django.test import SimpleTestCase

from api.reports import analytics, config, niveles, sections


AMENAZA_INCENDIO = 1
AMENAZA_SISMO = 3


def _contribuciones(filas):
    """Construye el DataFrame que consume `analytics.diagnostico`."""
    return pd.DataFrame(filas)


class DiagnosticoSinBase(SimpleTestCase):
    """El clasificador, sobre datos sintéticos: no necesita base de datos."""

    databases = []

    def _dataset(self, valores_por_sub):
        filas = []
        for sub_id, valores in valores_por_sub.items():
            for inm, valor in enumerate(valores):
                filas.append({
                    'id_inmueble': inm,
                    'subindicador_id': sub_id,
                    'subindicador_nombre': f'sub{sub_id}',
                    'indicador_id': 1,
                    'indicador_nombre': 'ind',
                    'valor': float(valor),
                    'peso_sub': 0.5,
                    'peso_ind': 1.0,
                    'contribucion': float(valor) * 0.5,
                })
        return _contribuciones(filas)

    def test_sub_indicador_constante_es_sistemico(self):
        """Todos puntúan 4: pesa pero no discrimina."""
        df = analytics.diagnostico(self._dataset({
            1: [4, 4, 4, 4, 4, 4],       # constante
            2: [1, 2, 3, 4, 1, 2],       # variable
        }))
        constante = df[df['factor_nombre'] == 'sub1'].iloc[0]
        self.assertTrue(constante['sin_variacion'])
        self.assertEqual(constante['correlacion'], 0.0)
        self.assertEqual(constante['clasificacion'], analytics.SISTEMICO)

    def test_sub_indicador_que_varia_con_el_resto_es_diferenciador(self):
        df = analytics.diagnostico(self._dataset({
            1: [1, 2, 3, 4, 1, 2],
            2: [1, 2, 3, 4, 1, 2],       # correlacionado con el anterior
        }), umbral_correlacion=0.4)
        self.assertIn(analytics.DIFERENCIADOR, set(df['clasificacion']))

    def test_correlacion_descuenta_el_aporte_propio(self):
        """Correlacionar contra el total completo inflaría el valor.

        Con un solo sub-indicador el "resto" es cero, así que la correlación
        debe ser nula y no 1, que es lo que daría contra el total.
        """
        df = analytics.diagnostico(self._dataset({1: [1, 2, 3, 4, 1, 2]}))
        self.assertEqual(df.iloc[0]['correlacion'], 0.0)

    def test_dataset_vacio_no_revienta(self):
        df = analytics.diagnostico(_contribuciones([]))
        self.assertTrue(df.empty)


def _base_disponible():
    try:
        from api.reports import queries
        queries.total_inmuebles()
        return True
    except Exception:
        return False


requiere_db = unittest.skipUnless(_base_disponible(), 'Base de datos no disponible')


@requiere_db
class AnalisisSobreDatosReales(SimpleTestCase):

    databases = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from api.reports.context import ReportContext
        cls.ctx = ReportContext(config.ReportConfig(amenaza_id=AMENAZA_INCENDIO))

    def test_plan_de_gestion_es_sistemico(self):
        """El hallazgo que motivó el rediseño: aporta mucho y no discrimina."""
        df = self.ctx.diagnostico
        fila = df[df['factor_nombre'].str.contains('Plan de gestión', case=False)].iloc[0]
        self.assertGreater(fila['valor_medio'], 3.9)
        self.assertGreater(fila['pct_alto'], 95)
        self.assertLess(abs(fila['correlacion']), 0.4)
        self.assertEqual(fila['clasificacion'], analytics.SISTEMICO)

    def test_aportes_suman_aproximadamente_cien(self):
        """El aporte es una descomposición del índice: debe cerrar en 100%."""
        self.assertAlmostEqual(self.ctx.diagnostico['aporte_pct'].sum(), 100.0, places=0)

    def test_los_dos_niveles_reparten_el_mismo_indice(self):
        """Agregar a indicador primario no puede cambiar el total repartido."""
        por_indicador = self.ctx.diagnostico_indicadores
        self.assertAlmostEqual(por_indicador['aporte_pct'].sum(), 100.0, places=0)
        self.assertEqual(len(por_indicador), len(self.ctx.indicadores))

    def test_el_aporte_del_indicador_es_la_suma_de_sus_subindicadores(self):
        sub = self.ctx.diagnostico.merge(
            self.ctx.contribuciones[['subindicador_id', 'indicador_nombre']].drop_duplicates(),
            left_on='factor_id', right_on='subindicador_id')
        por_grupo = sub.groupby('indicador_nombre')['aporte_pct'].sum()

        for _, fila in self.ctx.diagnostico_indicadores.iterrows():
            self.assertAlmostEqual(
                fila['aporte_pct'], por_grupo[fila['factor_nombre']], places=4,
                msg=f"El aporte de «{fila['factor_nombre']}» no cuadra con sus sub-indicadores")

    def test_el_puntaje_del_indicador_queda_en_la_escala_1_4(self):
        """Los pesos de los sub-indicadores suman 1 dentro de cada indicador."""
        valores = self.ctx.diagnostico_indicadores['valor_medio']
        self.assertGreaterEqual(valores.min(), 1.0)
        self.assertLessEqual(valores.max(), 4.0)


class RegistroDeSecciones(SimpleTestCase):

    databases = []

    def test_los_ordenes_son_unicos(self):
        ordenes = [s.orden for s in sections.REGISTRY.values()]
        self.assertEqual(len(ordenes), len(set(ordenes)), 'Hay secciones con el mismo orden')

    def test_el_modo_completo_incluye_todo_lo_del_ejecutivo(self):
        ejecutivo = {s.id for s in sections.REGISTRY.values() if config.MODO_EJECUTIVO in s.modos}
        completo = {s.id for s in sections.REGISTRY.values() if config.MODO_COMPLETO in s.modos}
        self.assertTrue(ejecutivo <= completo,
                        f'El ejecutivo tiene secciones que el completo no: {ejecutivo - completo}')

    def test_catalogo_expone_todas_las_secciones(self):
        self.assertEqual(len(sections.catalogo()), len(sections.REGISTRY))

    def test_seccion_desconocida_es_error(self):
        cfg = config.ReportConfig(amenaza_id=1, secciones=('no_existe',))
        with self.assertRaises(ValueError):
            sections.secciones_para(cfg, _CtxFalso())

    def test_modo_invalido_es_error(self):
        with self.assertRaises(ValueError):
            config.ReportConfig(amenaza_id=1, modo='raro')


class _CtxFalso:
    capacidades = frozenset()


@requiere_db
class GeneracionPorModo(SimpleTestCase):

    databases = []

    def test_el_ejecutivo_es_mas_corto_que_el_completo(self):
        import re
        from api.reports import pdf

        pdfs = {}
        for modo in (config.MODO_EJECUTIVO, config.MODO_COMPLETO):
            datos = pdf.generar(config.ReportConfig(amenaza_id=AMENAZA_SISMO, modo=modo))
            self.assertTrue(datos.startswith(b'%PDF'))
            pdfs[modo] = max(int(m) for m in re.findall(rb'/Count (\d+)', datos))

        self.assertLess(pdfs[config.MODO_EJECUTIVO], pdfs[config.MODO_COMPLETO])

    def test_una_sola_seccion_produce_un_documento_corto(self):
        """La lista blanca permite revisar una sección sin generar el informe entero."""
        import re
        from api.reports import pdf

        datos = pdf.generar(config.ReportConfig(
            amenaza_id=AMENAZA_SISMO, secciones=('portada', 'diagnostico_primarios'), incluir_indice=False))
        paginas = max(int(m) for m in re.findall(rb'/Count (\d+)', datos))
        self.assertLessEqual(paginas, 4)
