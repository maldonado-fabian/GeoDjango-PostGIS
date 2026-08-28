"""Registro de secciones del informe.

Cada sección es una función `build(ctx, cfg) -> [Flowable]`. No tocan una lista
compartida, no emiten sus propios saltos de página y no construyen el documento:
de eso se encarga el orquestador. Así una sección se puede armar y revisar sola,
sin generar un PDF entero.

Los dos modos del informe son un filtro sobre este registro, no dos caminos de
código.
"""

from dataclasses import dataclass, field
from typing import Callable

from ..config import MODO_COMPLETO, MODO_EJECUTIVO


@dataclass(frozen=True)
class Section:
    id: str
    titulo: str
    orden: int
    modos: frozenset
    build: Callable
    #: Capacidades que `ReportContext` debe declarar para que la sección exista.
    requiere: tuple = ()
    #: Si False, la sección continúa en la página anterior.
    salto_previo: bool = True


REGISTRY = {}


def register(seccion):
    if seccion.id in REGISTRY:
        raise ValueError(f'Sección duplicada: {seccion.id}')
    REGISTRY[seccion.id] = seccion
    return seccion


def seccion(id, titulo, orden, *, modos=(MODO_EJECUTIVO, MODO_COMPLETO),
            requiere=(), salto_previo=True):
    """Decorador que registra la función como sección."""
    def envolver(fn):
        register(Section(
            id=id, titulo=titulo, orden=orden, modos=frozenset(modos),
            build=fn, requiere=tuple(requiere), salto_previo=salto_previo,
        ))
        return fn
    return envolver


def secciones_para(cfg, ctx):
    """Secciones aplicables, ordenadas.

    Filtra por lista blanca explícita si la hay, si no por modo; después quita
    las excluidas y las que no tienen datos para existir.
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
        elegidas = [s for s in REGISTRY.values() if cfg.modo in s.modos]

    elegidas = [s for s in elegidas if s.id not in set(cfg.excluir)]
    elegidas = [s for s in elegidas if set(s.requiere) <= ctx.capacidades]
    return sorted(elegidas, key=lambda s: s.orden)


def catalogo():
    """Descripción del registro, para exponerla por la API."""
    return [
        {
            'id': s.id,
            'titulo': s.titulo,
            'orden': s.orden,
            'modos': sorted(s.modos),
            'requiere': list(s.requiere),
        }
        for s in sorted(REGISTRY.values(), key=lambda s: s.orden)
    ]


# El import va al final: los módulos de secciones importan `seccion` de aquí.
from . import documento, amenaza, analisis  # noqa: E402,F401
