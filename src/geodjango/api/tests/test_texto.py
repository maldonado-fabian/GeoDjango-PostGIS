"""El texto narrativo no puede afirmar cosas de una amenaza en otra.

El informe de Sismo llegó a producirse con conclusiones sobre "la gestión del
fuego" y "un plan de gestión de incendios", porque esas frases estaban escritas
dentro de una plantilla genérica. Estos tests impiden que vuelva a pasar.
"""

from django.test import SimpleTestCase

from api.reports import niveles, text


def _filas(bajo=0, medio=0, alto=0, muy_alto=0, no_evaluado=0):
    """Filas de conteo con los porcentajes ya calculados sobre el total."""
    crudos = {
        niveles.NIVEL_BAJO: bajo,
        niveles.NIVEL_MEDIO: medio,
        niveles.NIVEL_ALTO: alto,
        niveles.NIVEL_MUY_ALTO: muy_alto,
        niveles.NIVEL_NO_EVALUADO: no_evaluado,
    }
    total = sum(crudos.values()) or 1
    return [
        {'nivel': n, 'cantidad': c, 'porcentaje': round(c / total * 100)}
        for n, c in crudos.items()
    ]


class SinFugasEntreAmenazas(SimpleTestCase):

    databases = []

    #: Términos propios de una amenaza que no deben aparecer en otra.
    TERMINOS_INCENDIO = ('incendio', 'fuego', 'cortafuego')

    def test_conclusiones_de_sismo_no_hablan_de_incendio(self):
        texto = text.conclusiones(_filas(bajo=100, medio=150, alto=80, muy_alto=21), 'Sismo').lower()
        for termino in self.TERMINOS_INCENDIO:
            self.assertNotIn(termino, texto, f'La conclusión de Sismo menciona «{termino}»')

    def test_conclusiones_de_incendio_conservan_su_nota_cualitativa(self):
        """Lo específico de Incendio no se perdió: se movió a NOTAS_POR_AMENAZA."""
        texto = text.conclusiones(_filas(alto=200, muy_alto=100, no_evaluado=69), 'Incendio').lower()
        self.assertIn('incendio', texto)
        self.assertIn('gestión del fuego', texto)

    def test_amenaza_sin_nota_no_inventa_contenido(self):
        """Una amenaza nueva se limita a lo que dicen los números."""
        texto = text.conclusiones(_filas(bajo=300), 'Remoción en masa')
        self.assertIn('remoción en masa', texto.lower())
        self.assertNotIn('None', texto)

    def test_parrafo_evaluados_nombra_la_amenaza(self):
        texto = text.parrafo_evaluados(369, 18, 'Sismo').lower()
        self.assertIn('sismo', texto)
        for termino in self.TERMINOS_INCENDIO:
            self.assertNotIn(termino, texto)


class VeredictoDerivadoDeLosDatos(SimpleTestCase):
    """Antes la conclusión afirmaba "alto índice de vulnerabilidad" siempre."""

    databases = []

    def test_mayoria_alta_da_veredicto_alto(self):
        texto = text.conclusiones(_filas(alto=200, muy_alto=100, bajo=51), 'Sismo')
        self.assertIn('un alto índice de vulnerabilidad', texto)

    def test_mayoria_baja_no_afirma_alta_vulnerabilidad(self):
        texto = text.conclusiones(_filas(bajo=340, medio=10, alto=1), 'Sismo')
        self.assertNotIn('un alto índice de vulnerabilidad', texto)
        self.assertIn('acotada', texto)


class RedaccionRobusta(SimpleTestCase):

    databases = []

    def test_una_sola_amenaza_no_produce_frase_de_ranking(self):
        """Con una amenaza, "son, en primer lugar, X" es agramatical."""
        texto = text.parrafo_promedios([
            {'nombre': 'Incendio', 'promedio': 2.73, 'nivel': niveles.NIVEL_ALTO},
        ])
        self.assertNotIn('en primer lugar', texto)
        self.assertIn('2,73', texto)

    def test_varias_amenazas_se_enumeran(self):
        texto = text.parrafo_promedios([
            {'nombre': 'Incendio', 'promedio': 2.73, 'nivel': niveles.NIVEL_ALTO},
            {'nombre': 'Sismo', 'promedio': 1.91, 'nivel': niveles.NIVEL_MEDIO},
        ])
        self.assertIn('en primer lugar', texto)
        self.assertIn('2,73', texto)
        self.assertIn('1,91', texto)

    def test_los_decimales_usan_coma_y_no_corrompen_el_nombre(self):
        """El reemplazo de punto por coma se aplica al número, no a la frase.

        Antes se hacía sobre el segmento completo, así que un nombre de amenaza
        con punto quedaba alterado.
        """
        texto = text.parrafo_promedios([
            {'nombre': 'Sismo (M. Richter)', 'promedio': 1.91, 'nivel': niveles.NIVEL_MEDIO},
        ])
        self.assertIn('m. richter', texto.lower())
        self.assertIn('1,91', texto)

    def test_distribucion_se_describe_en_orden_de_magnitud(self):
        """El nivel dominante se menciona primero, no en un orden fijo."""
        texto = text.parrafo_resultados_amenaza(
            _filas(bajo=300, medio=30, alto=10, muy_alto=5, no_evaluado=24), 369)
        pos_bajo = texto.lower().index('bajo')
        pos_alto = texto.lower().index('alto')
        self.assertLess(pos_bajo, pos_alto, 'El nivel dominante debe aparecer primero')

    def test_sin_evaluaciones_no_revienta(self):
        texto = text.parrafo_resultados_amenaza(_filas(no_evaluado=369), 369)
        self.assertIn('ninguno', texto.lower())
