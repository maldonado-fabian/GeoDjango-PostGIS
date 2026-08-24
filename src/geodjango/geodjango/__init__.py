# Asegura que la app de Celery se cargue al iniciar Django,
# para que las tareas con @shared_task usen esta instancia.
from .celery import app as celery_app

__all__ = ('celery_app',)
