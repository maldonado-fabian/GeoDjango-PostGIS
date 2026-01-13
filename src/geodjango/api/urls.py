from django.urls import path
from . import views

urlpatterns = [
    path('amenazas/',views.lista_amenazas)]