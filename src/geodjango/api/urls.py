from django.urls import path
from . import views

urlpatterns = [
    #Amenazas URLs
    path('amenazas/',views.lista_amenazas)
    ,path('amenazas/<int:pk>/',views.detalle_amenaza)
    ,path('amenazas/crear/',views.crear_amenaza)
    ,path('amenazas/actualizar/<int:pk>/',views.actualizar_amenaza)

    #Clases URLs
    ,path('clases/',views.lista_clases)
    ,path('clases/<int:pk>/',views.detalle_clase)
    ,path('clases/crear/',views.crear_clase)
    ,path('clases/actualizar/<int:pk>/',views.actualizar_clase)

    #Evaluacion URLs
    ,path('evaluacion/',views.lista_evaluaciones)
    ,path('evaluacion/<int:pk>/',views.detalle_evaluacion)
    ,path('evaluacion/crear/',views.crear_evaluacion)
    ,path('evaluacion/actualizar/<int:pk>/',views.actualizar_evaluacion)

    #Indicadores URLs
    ,path('indicadores/',views.lista_indicadores)
    ,path('indicadores/<int:pk>/',views.detalle_indicador)
    ,path('indicadores/crear/',views.crear_indicador)
    ,path('indicadores/actualizar/<int:pk>/',views.actualizar_indicador)

    #SubIndicadores URLs
    ,path('subindicadores/',views.lista_subindicadores)
    ,path('subindicadores/<int:pk>/',views.detalle_subindicador)
    ,path('subindicadores/crear/',views.crear_subindicador)
    ,path('subindicadores/actualizar/<int:pk>/',views.actualizar_subindicador)

    #Inmuebles URLs
    ,path('inmuebles/',views.lista_inmuebles)
    ,path('inmuebles/<int:pk>/',views.detalle_inmueble)
    ,path('inmuebles/crear/',views.crear_inmueble)
    ,path('inmuebles/actualizar/<int:pk>/',views.actualizar_inmueble)

    ,path('procesar-kmz/', views.ProcesarKMZView.as_view(), name='procesar-kmz')

    # Crear SHP
    ,path('crear-shp/', views.CrearSHPView.as_view(), name='crear-shp')
]

 
