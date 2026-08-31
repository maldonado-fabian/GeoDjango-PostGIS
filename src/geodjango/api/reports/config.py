"""Configuración del informe.

Un solo informe por amenaza: no hay elección de modo ni de secciones desde la
API. `secciones`/`excluir` quedan como parámetros internos, útiles para armar
un documento con una sola sección al revisarla en tests.
"""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ReportConfig:
    """Qué informe se quiere."""

    amenaza_id: int

    #: Uso interno (tests): lista blanca explícita o exclusión de secciones.
    secciones: tuple = None
    excluir: tuple = ()

    dpi_mapa: int = 110
    dpi_dona: int = 100
    basemap: bool = True
    incluir_indice: bool = True

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
