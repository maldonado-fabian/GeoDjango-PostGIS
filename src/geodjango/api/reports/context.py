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


class ReportContext:
    """Acceso memoizado a todo lo que el informe necesita."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.figura = Contador()
        self.tabla = Contador()

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

    @cached_property
    def geo_manzanas(self):
        return queries.manzanas_geo()

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
            ['id_inmueble', 'subindicador_id', 'subindicador_nombre', 'indicador_nombre', 'valor']
        ]

    # ── análisis ─────────────────────────────────────────────────────────────

    @cached_property
    def diagnostico(self):
        return analytics.diagnostico(self.contribuciones, self.cfg.umbral_correlacion)

    @cached_property
    def territorial(self):
        return analytics.territorial(self.indice(), self.meta)

    @cached_property
    def criticos(self):
        return analytics.criticos(
            self.contribuciones, self.meta, self.etiquetas_clase, top=self.cfg.top_criticos)

    @cached_property
    def distribucion(self):
        return analytics.resumen_distribucion(self.indice())

    @cached_property
    def amenaza_comparacion(self):
        """Amenaza con la que cruzar, o `None` si no hay otra evaluada.

        Si la configuración no la fija, se elige la que comparta más inmuebles
        evaluados con la principal: es la que produce un cruce con sentido.
        """
        if self.cfg.amenaza_comparacion is not None:
            fila = queries.amenaza(self.cfg.amenaza_comparacion)
            return fila if fila and int(fila['id']) != self.amenaza_id else None

        propios = set(self.indice()['id_inmueble'])
        mejor, mejor_n = None, 0
        for _, a in self.amenazas.iterrows():
            otro_id = int(a['id'])
            if otro_id == self.amenaza_id:
                continue
            comunes = len(propios & set(self.indice(otro_id)['id_inmueble']))
            if comunes > mejor_n:
                mejor, mejor_n = a.to_dict(), comunes
        return mejor

    @cached_property
    def cruce(self):
        otra = self.amenaza_comparacion
        if otra is None:
            return None
        return analytics.cruce(
            self.indice(), self.indice(int(otra['id'])), self.meta,
            nombre_a=self.nombre_amenaza, nombre_b=otra['nombre'],
        )

    # ── capacidades ──────────────────────────────────────────────────────────

    @cached_property
    def capacidades(self):
        """Qué secciones tienen datos para existir.

        Una sección sin datos se omite con una nota, en vez de producir una
        página vacía o reventar el worker.
        """
        caps = set()
        if len(self.amenazas) > 1 and self.cruce is not None:
            caps.add('multi_amenaza')
        if not self.territorial.empty:
            caps.add('territorial')
        if not self.diagnostico.empty:
            caps.add('diagnostico')
        if not self.criticos.empty:
            caps.add('criticos')
        return frozenset(caps)
