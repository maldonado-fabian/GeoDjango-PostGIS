import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geodjango.settings')

app = Celery('geodjango')

# Toma la configuración desde settings.py usando el prefijo CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubre tareas en tasks.py de cada app instalada (api/tasks.py)
app.autodiscover_tasks()
