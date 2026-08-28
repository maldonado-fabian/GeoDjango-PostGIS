"""Configuración del informe.

El modo es un parámetro, no dos caminos de código: la versión ejecutiva y la
completa son el mismo documento con distinto conjunto de secciones y un par de
interruptores dentro de ellas.
"""

from dataclasses import dataclass, replace


MODO_EJECUTIVO = 'ejecutivo'
MODO_COMPLETO = 'completo'
MODOS = (MODO_EJECUTIVO, MODO_COMPLETO)


@dataclass(frozen=True)
class ReportConfig:
    """Qué informe se quiere.

    `secciones` es una lista blanca explícita que ignora la pertenencia al modo;
    sirve para pedir un documento con una sola sección al revisarla. `excluir`
    quita secciones sin tener que enumerar el resto.
    """

    amenaza_id: int
    modo: str = MODO_EJECUTIVO

    secciones: tuple = None
    excluir: tuple = ()

    #: Amenaza contra la que comparar en la sección multi-amenaza. `None` elige
    #: automáticamente la que comparta más inmuebles evaluados con la principal.
    amenaza_comparacion: int = None

    top_criticos: int = 25
    top_manzanas: int = 10

    #: Correlación desde la cual un sub-indicador se considera diferenciador.
    umbral_correlacion: float = 0.40

    dpi_mapa: int = 110
    dpi_dona: int = 100
    basemap: bool = True
    incluir_indice: bool = True

    #: Advertencia de distribución en la portada. La sección de inmuebles
    #: críticos publica direcciones y roles SII de los predios más vulnerables.
    restringido: bool = True

    def __post_init__(self):
        if self.modo not in MODOS:
            raise ValueError(f'Modo desconocido: {self.modo!r}. Válidos: {", ".join(MODOS)}')
        if self.top_criticos < 1:
            raise ValueError('top_criticos debe ser al menos 1')

    @property
    def es_completo(self):
        return self.modo == MODO_COMPLETO

    def con(self, **cambios):
        return replace(self, **cambios)

    @classmethod
    def desde_dict(cls, datos):
        """Construye desde un dict de la API, ignorando claves desconocidas."""
        validas = {f.name for f in cls.__dataclass_fields__.values()}
        filtrado = {k: v for k, v in (datos or {}).items() if k in validas and v is not None}
        for clave in ('secciones', 'excluir'):
            if clave in filtrado and filtrado[clave] is not None:
                filtrado[clave] = tuple(filtrado[clave])
        return cls(**filtrado)
