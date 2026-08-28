"""Tests de integración del informe PDF.

Son de integración a propósito: las tablas del dominio son `managed = False`, así
que Django no las crea en la base de test. `api/reports/queries.py` abre su propia
conexión SQLAlchemy desde las variables `DATABASE_*`, por lo que estos tests leen
la base real de desarrollo (sólo SELECT, nunca escriben).

Los números esperados corresponden al dataset cargado el 2026-08-28: 369 inmuebles,
351 evaluados en Incendio (id 1) y en Sismo (id 3). Si el dataset cambia, estos
tests fallan a propósito: son la línea base contra la que se compara el rediseño.
"""

import unittest

from django.test import SimpleTestCase

from api.reports import niveles, queries


AMENAZA_INCENDIO = 1
AMENAZA_SISMO = 3

TOTAL_INMUEBLES = 369
EVALUADOS = 351


def _base_disponible():
    try:
        queries.total_inmuebles()
        return True
    except Exception:
        return False


DB = _base_disponible()
requiere_db = unittest.skipUnless(DB, 'Base de datos no disponible')


@requiere_db
class DatosBase(SimpleTestCase):
    """Línea base del dataset. Si esto cambia, el resto de los números cambia."""

    databases = []

    def test_total_inmuebles(self):
        self.assertEqual(queries.total_inmuebles(), TOTAL_INMUEBLES)

    def test_amenazas_registradas(self):
        df = queries.amenazas()
        nombres = dict(zip(df['id'], df['nombre']))
        self.assertEqual(nombres.get(AMENAZA_INCENDIO), 'Incendio')
        self.assertEqual(nombres.get(AMENAZA_SISMO), 'Sismo')

    def test_cobertura_por_amenaza(self):
        """Ambas amenazas cubren los mismos 351 inmuebles."""
        for amenaza_id in (AMENAZA_INCENDIO, AMENAZA_SISMO):
            with self.subTest(amenaza=amenaza_id):
                self.assertEqual(len(queries.indice_por_inmueble(amenaza_id)), EVALUADOS)


@requiere_db
class DistribucionDelIndice(SimpleTestCase):
    """Estadística descriptiva del índice: hoy el informe no la muestra."""

    databases = []

    ESPERADO = {
        AMENAZA_INCENDIO: {'media': 2.73, 'mediana': 2.77, 'desv': 0.39, 'min': 1.00, 'max': 3.71},
        AMENAZA_SISMO:    {'media': 1.91, 'mediana': 1.81, 'desv': 0.40, 'min': 1.285, 'max': 3.25},
    }

    def test_estadistica_descriptiva(self):
        for amenaza_id, esperado in self.ESPERADO.items():
            serie = queries.indice_por_inmueble(amenaza_id)['indice_de_riesgo']
            with self.subTest(amenaza=amenaza_id):
                self.assertAlmostEqual(serie.mean(), esperado['media'], places=2)
                self.assertAlmostEqual(serie.median(), esperado['mediana'], places=2)
                self.assertAlmostEqual(serie.std(), esperado['desv'], places=2)
                self.assertAlmostEqual(serie.min(), esperado['min'], places=2)
                self.assertAlmostEqual(serie.max(), esperado['max'], places=2)

    def test_indice_dentro_de_la_escala(self):
        """Ningún inmueble puede caer fuera de 1–4: delataría pesos mal sumados."""
        for amenaza_id in self.ESPERADO:
            serie = queries.indice_por_inmueble(amenaza_id)['indice_de_riesgo']
            with self.subTest(amenaza=amenaza_id):
                self.assertGreaterEqual(serie.min(), 1.0)
                self.assertLessEqual(serie.max(), 4.0)


@requiere_db
class CorrelacionEntreAmenazas(SimpleTestCase):
    """Base del análisis multi-amenaza."""

    databases = []

    def test_correlacion_incendio_sismo(self):
        inc = queries.indice_por_inmueble(AMENAZA_INCENDIO).set_index('id_inmueble')['indice_de_riesgo']
        sis = queries.indice_por_inmueble(AMENAZA_SISMO).set_index('id_inmueble')['indice_de_riesgo']
        comun = inc.index.intersection(sis.index)

        self.assertEqual(len(comun), EVALUADOS, 'Ambas amenazas deben cubrir los mismos inmuebles')
        self.assertAlmostEqual(inc[comun].corr(sis[comun]), 0.462, places=2)

    def test_inmuebles_alto_en_ambas_amenazas(self):
        """Los 37 inmuebles Alto+ en ambas: la lista de priorización multi-riesgo."""
        inc = queries.indice_por_inmueble(AMENAZA_INCENDIO).set_index('id_inmueble')['indice_de_riesgo']
        sis = queries.indice_por_inmueble(AMENAZA_SISMO).set_index('id_inmueble')['indice_de_riesgo']
        comun = inc.index.intersection(sis.index)

        altos_en_ambas = sum(
            1 for i in comun
            if niveles.nivel_por_indice(inc[i]) in (niveles.NIVEL_ALTO, niveles.NIVEL_MUY_ALTO)
            and niveles.nivel_por_indice(sis[i]) in (niveles.NIVEL_ALTO, niveles.NIVEL_MUY_ALTO)
        )
        self.assertEqual(altos_en_ambas, 37)


@requiere_db
class EstructuraDeIndicadores(SimpleTestCase):
    """Los pesos son el corazón del método: si no suman 1, el índice se desescala."""

    databases = []

    def test_conteo_de_indicadores(self):
        self.assertEqual(len(queries.indicadores(AMENAZA_INCENDIO)), 4)
        self.assertEqual(len(queries.indicadores(AMENAZA_SISMO)), 6)

    def test_subindicadores_por_amenaza(self):
        for amenaza_id, esperado in ((AMENAZA_INCENDIO, 20), (AMENAZA_SISMO, 19)):
            df = queries.subindicador_valores(amenaza_id)
            with self.subTest(amenaza=amenaza_id):
                self.assertEqual(df['subindicador_nombre'].nunique(), esperado)

    def test_valores_crudos_en_escala_1_4(self):
        for amenaza_id in (AMENAZA_INCENDIO, AMENAZA_SISMO):
            serie = queries.subindicador_valores(amenaza_id)['valor']
            with self.subTest(amenaza=amenaza_id):
                self.assertGreaterEqual(serie.min(), 1)
                self.assertLessEqual(serie.max(), 4)


@requiere_db
class GeneracionDelPDF(SimpleTestCase):
    """Smoke test: el informe se arma de punta a punta para ambas amenazas.

    Es lento (renderiza mapas con matplotlib), pero es la única prueba de que el
    documento no revienta al cambiar de amenaza.
    """

    databases = []

    def _generar(self, amenaza_id):
        from api.reports.pdf import generar_pdf_resumen
        return generar_pdf_resumen(amenaza_id)

    def test_incendio_produce_un_pdf(self):
        pdf = self._generar(AMENAZA_INCENDIO)
        self.assertTrue(pdf.startswith(b'%PDF'), 'La salida no es un PDF')
        self.assertGreater(len(pdf), 100_000)

    def test_sismo_produce_un_pdf(self):
        pdf = self._generar(AMENAZA_SISMO)
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertGreater(len(pdf), 100_000)

    def test_amenaza_inexistente_no_debe_producir_un_informe_de_incendio(self):
        """Hoy `pdf.py` cae al literal "Incendio" ante un id desconocido.

        Se documenta como fallo esperado: la Fase 3 debe convertirlo en un error
        explícito en vez de un informe silenciosamente equivocado.
        """
        with self.assertRaises(Exception):
            self._generar(99999)
