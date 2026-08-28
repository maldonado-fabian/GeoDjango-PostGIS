"""Registro de secciones del informe.

Cada sección es una función `build(ctx, cfg) -> [Flowable]`. No tocan una lista
compartida y no emiten sus propios saltos de página: de eso se encarga el
orquestador. Así una sección se puede armar y revisar sola, sin generar un PDF
entero.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Section:
    id: str
    titulo: str
    orden: int
    build: Callable
    #: Si False, la sección continúa en la página anterior.
    salto_previo: bool = True


REGISTRY = {}


def register(seccion):
    if seccion.id in REGISTRY:
        raise ValueError(f'Sección duplicada: {seccion.id}')
    REGISTRY[seccion.id] = seccion
    return seccion


def seccion(id, titulo, orden, *, salto_previo=True):
    """Decorador que registra la función como sección."""
    def envolver(fn):
        register(Section(id=id, titulo=titulo, orden=orden, build=fn, salto_previo=salto_previo))
        return fn
    return envolver


def secciones_para(cfg):
    """Secciones aplicables, ordenadas.

    Filtra por lista blanca explícita si la hay (`cfg.secciones`, uso interno
    para revisar una sección aislada); si no, todas las registradas. Después
    quita las excluidas.
    """
    if cfg.secciones:
        desconocidas = set(cfg.secciones) - set(REGISTRY)
        if desconocidas:
            raise ValueError(
                f'Secciones desconocidas: {", ".join(sorted(desconocidas))}. '
                f'Disponibles: {", ".join(sorted(REGISTRY))}'
            )
        elegidas = [REGISTRY[i] for i in cfg.secciones]
    else:
        elegidas = list(REGISTRY.values())

    elegidas = [s for s in elegidas if s.id not in set(cfg.excluir)]
    return sorted(elegidas, key=lambda s: s.orden)


# El import va al final: los módulos de secciones importan `seccion` de aquí.
from . import documento, amenaza  # noqa: E402,F401
