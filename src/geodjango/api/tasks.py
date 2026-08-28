"""Tareas Celery del API."""

import os
import re
import unicodedata

from celery import shared_task
from django.conf import settings

from .reports import pdf
from .reports.config import ReportConfig


def _slug(texto):
    """'Remoción en masa' -> 'remocion-en-masa'."""
    normalizado = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', normalizado.lower()).strip('-') or 'riesgo'


@shared_task(bind=True, soft_time_limit=600, time_limit=900)
def generar_pdf_resumen_task(self, amenaza_id=1):
    """Genera el informe de la amenaza y lo guarda en MEDIA_ROOT/reportes/.

    El nombre del archivo lleva la amenaza: sin eso, los informes de dos
    amenazas distintas llegan a la carpeta de descargas con nombres
    indistinguibles.
    """
    cfg = ReportConfig(amenaza_id=int(amenaza_id))
    pdf_bytes = pdf.generar(cfg)

    from .reports import queries
    amenaza = queries.amenaza(cfg.amenaza_id)
    nombre_amenaza = _slug(amenaza['nombre'] if amenaza else 'riesgo')

    carpeta = os.path.join(settings.MEDIA_ROOT, 'reportes')
    os.makedirs(carpeta, exist_ok=True)
    nombre = f'riesgo_{nombre_amenaza}_{self.request.id}.pdf'
    ruta = os.path.join(carpeta, nombre)
    with open(ruta, 'wb') as fh:
        fh.write(pdf_bytes)

    return {'archivo': nombre, 'ruta': ruta, 'amenaza_id': cfg.amenaza_id}
