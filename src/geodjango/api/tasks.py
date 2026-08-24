"""Tareas Celery del API."""

import os

from celery import shared_task
from django.conf import settings

from .reports.pdf import generar_pdf_resumen


@shared_task(bind=True)
def generar_pdf_resumen_task(self, amenaza_id=1):
    """Genera el PDF de resumen y lo guarda en MEDIA_ROOT/reportes/<task_id>.pdf.

    Devuelve metadatos (ruta relativa y nombre) que el endpoint de descarga usa.
    """
    pdf_bytes = generar_pdf_resumen(int(amenaza_id))

    carpeta = os.path.join(settings.MEDIA_ROOT, "reportes")
    os.makedirs(carpeta, exist_ok=True)
    nombre = f"resumen_riesgo_{self.request.id}.pdf"
    ruta = os.path.join(carpeta, nombre)
    with open(ruta, "wb") as fh:
        fh.write(pdf_bytes)

    return {"archivo": nombre, "ruta": ruta}
