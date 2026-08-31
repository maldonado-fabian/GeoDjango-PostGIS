"""Datos del informe, cargados una vez.

Antes cada figura pedía lo suyo por su cuenta: el índice de la amenaza objetivo
se consultaba dos veces y la geometría base una vez por familia de figuras.
Aquí todo se memoiza y las secciones comparten el mismo `ReportContext`.

También lleva los contadores de figura y tabla, para que su numeración dependa
del orden real de armado y no de un `start=3` escrito a mano.
"""

from functools import cached_property

from . import analytics, niveles, queries


class Contador:
    """Numeración correlativa de figuras o tablas."""

    def __init__(self):
        self._n = 0

    def siguiente(self):
        self._n += 1
        return self._n

    @property
    def actual(self):
        return self._n


class Numerador:
    """Numeración de secciones: "3. Título" / "3.1 Subtítulo".

    Cada llamada a `h1()` avanza el contador principal y reinicia el de
    sub-secciones; `h2()` avanza el sub-contador bajo el h1 actual. No valida
    que h2() se llame después de un h1(): si se usa antes, numera bajo "0".
    """

    def __init__(self):
        self._n1 = 0
        self._n2 = 0

    def h1(self, titulo):
        self._n1 += 1
        self._n2 = 0
        return f'{self._n1}. {titulo}'

    def h2(self, titulo):
        self._n2 += 1
        return f'{self._n1}.{self._n2} {titulo}'


class ReportContext:
    """Acceso memoizado a todo lo que el informe necesita."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.figura = Contador()
        self.tabla = Contador()
        self.titulos = Numerador()

        self.amenaza = queries.amenaza(cfg.amenaza_id)
        if self.amenaza is None:
            raise ValueError(f'No existe la amenaza con id {cfg.amenaza_id}')

    # ── identidad ────────────────────────────────────────────────────────────

    @property
    def amenaza_id(self):
        return int(self.amenaza['id'])

    @property
    def nombre_amenaza(self):
        return self.amenaza['nombre']

    # ── catálogo ─────────────────────────────────────────────────────────────

    @cached_property
    def amenazas(self):
        return queries.amenazas()

    @cached_property
    def indicadores(self):
        return queries.indicadores(self.amenaza_id)

    @cached_property
    def etiquetas_clase(self):
        return queries.etiquetas_clase(self.amenaza_id)

    # ── inmuebles ────────────────────────────────────────────────────────────

    @cached_property
    def total_inmuebles(self):
        return queries.total_inmuebles()

    @cached_property
    def meta(self):
        return queries.inmuebles_meta()

    @cached_property
    def geo(self):
        return queries.inmuebles_geo()

    # ── evaluación ───────────────────────────────────────────────────────────

    def indice(self, amenaza_id=None):
        """Índice por inmueble, memoizado por amenaza."""
        amenaza_id = int(amenaza_id or self.amenaza_id)
        if not hasattr(self, '_indices'):
            self._indices = {}
        if amenaza_id not in self._indices:
            self._indices[amenaza_id] = queries.indice_por_inmueble(amenaza_id)
        return self._indices[amenaza_id]

    def filas_nivel(self, amenaza_id=None):
        """Conteo por nivel, con los no evaluados imputados sobre el total del sitio."""
        idx = self.indice(amenaza_id)
        nivs = [niveles.nivel_por_indice(v) for v in idx['indice_de_riesgo']]
        return niveles.conteo(nivs, self.total_inmuebles)

    def promedio(self, amenaza_id=None):
        idx = self.indice(amenaza_id)
        return float(idx['indice_de_riesgo'].mean()) if len(idx) else 0.0

    @cached_property
    def contribuciones(self):
        return queries.contribuciones(self.amenaza_id)

    @cached_property
    def indicador_scores(self):
        return queries.indicador_scores(self.amenaza_id)

    @cached_property
    def subindicador_valores(self):
        return self.contribuciones[
            ['id_inmueble', 'subindicador_id', 'subindicador_nombre',
             'subindicador_descripcion', 'indicador_nombre', 'valor']
        ]

    # ── análisis ─────────────────────────────────────────────────────────────

    @cached_property
    def aporte_indicadores(self):
        """Cuánto aporta cada indicador primario al índice de riesgo."""
        return analytics.aporte_por_factor(self.contribuciones, nivel=analytics.NIVEL_INDICADOR)

    @cached_property
    def aporte_subindicadores(self):
        """Cuánto aporta cada indicador secundario al índice de riesgo."""
        return analytics.aporte_por_factor(self.contribuciones, nivel=analytics.NIVEL_SUBINDICADOR)

    @cached_property
    def distribucion(self):
        return analytics.resumen_distribucion(self.indice())
