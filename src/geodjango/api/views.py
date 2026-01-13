from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Amenazas, Clases, Evaluacion, Indicadores, Inmuebles, SubIndicadores
from .serializers import AmenazasSerializer, ClasesSerializer, EvaluacionSerializer, IndicadoresSerializer, InmueblesSerializer, SubIndicadoresSerializer



# Create your views here.

#Amenazas Views
@api_view(['GET'])
def lista_amenazas(request):
    amenazas = Amenazas.objects.all()
    serializer = AmenazasSerializer(amenazas, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def detalle_amenaza(request, pk):
    try:
        amenaza = Amenazas.objects.get(pk=pk)
    except Amenazas.DoesNotExist:
        return Response({'error': 'Amenaza no encontrada'}, status=404)

    serializer = AmenazasSerializer(amenaza)
    return Response(serializer.data)

@api_view(['POST'])
def crear_amenaza(request):
    serializer = AmenazasSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

@api_view(['PUT'])
def actualizar_amenaza(request, pk):
    try:
        amenaza = Amenazas.objects.get(pk=pk)
    except Amenazas.DoesNotExist:
        return Response({'error': 'Amenaza no encontrada'}, status=404)

    serializer = AmenazasSerializer(amenaza, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


#Clases Views
@api_view(['GET'])
def lista_clases(request):
    clases = Clases.objects.all()
    serializer = ClasesSerializer(clases, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def detalle_clase(request, pk):
    try:
        clase = Clases.objects.get(pk=pk)
    except Clases.DoesNotExist:
        return Response({'error': 'Clase no encontrada'}, status=404)

    serializer = ClasesSerializer(clase)
    return Response(serializer.data)

@api_view(['POST'])
def crear_clase(request):
    serializer = ClasesSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

@api_view(['PUT'])
def actualizar_clase(request, pk):
    try:
        clase = Clases.objects.get(pk=pk)
    except Clases.DoesNotExist:
        return Response({'error': 'Clase no encontrada'}, status=404)

    serializer = ClasesSerializer(clase, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)

#Evaluacion Views
@api_view(['GET'])
def lista_evaluaciones(request):
    evaluaciones = Evaluacion.objects.all()
    serializer = EvaluacionSerializer(evaluaciones, many=True)
    return Response(serializer.data)
@api_view(['GET'])
def detalle_evaluacion(request, pk):
    try:
        evaluacion = Evaluacion.objects.get(pk=pk)
    except Evaluacion.DoesNotExist:
        return Response({'error': 'Evaluacion no encontrada'}, status=404)

    serializer = EvaluacionSerializer(evaluacion)
    return Response(serializer.data)

@api_view(['POST'])
def crear_evaluacion(request):
    serializer = EvaluacionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

@api_view(['PUT'])
def actualizar_evaluacion(request, pk):
    try:
        evaluacion = Evaluacion.objects.get(pk=pk)
    except Evaluacion.DoesNotExist:
        return Response({'error': 'Evaluacion no encontrada'}, status=404)

    serializer = EvaluacionSerializer(evaluacion, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)

#Indicadores Views
@api_view(['GET'])
def lista_indicadores(request):
    indicadores = Indicadores.objects.all()
    serializer = IndicadoresSerializer(indicadores, many=True)
    return Response(serializer.data)
@api_view(['GET'])
def detalle_indicador(request, pk):
    try:
        indicador = Indicadores.objects.get(pk=pk)
    except Indicadores.DoesNotExist:
        return Response({'error': 'Indicador no encontrado'}, status=404)

    serializer = IndicadoresSerializer(indicador)
    return Response(serializer.data)
@api_view(['POST'])
def crear_indicador(request):
    serializer = IndicadoresSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
@api_view(['PUT'])
def actualizar_indicador(request, pk):
    try:
        indicador = Indicadores.objects.get(pk=pk)
    except Indicadores.DoesNotExist:
        return Response({'error': 'Indicador no encontrado'}, status=404)

    serializer = IndicadoresSerializer(indicador, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)

#SubIndicadores Views
@api_view(['GET'])
def lista_subindicadores(request):
    subindicadores = SubIndicadores.objects.all()
    serializer = SubIndicadoresSerializer(subindicadores, many=True)
    return Response(serializer.data)
@api_view(['GET'])
def detalle_subindicador(request, pk):
    try:
        subindicador = SubIndicadores.objects.get(pk=pk)
    except SubIndicadores.DoesNotExist:
        return Response({'error': 'SubIndicador no encontrado'}, status=404)

    serializer = SubIndicadoresSerializer(subindicador)
    return Response(serializer.data)
@api_view(['POST'])
def crear_subindicador(request):
    serializer = SubIndicadoresSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
@api_view(['PUT'])
def actualizar_subindicador(request, pk):
    try:
        subindicador = SubIndicadores.objects.get(pk=pk)
    except SubIndicadores.DoesNotExist:
        return Response({'error': 'SubIndicador no encontrado'}, status=404)

    serializer = SubIndicadoresSerializer(subindicador, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


#Inmuebles Views
@api_view(['GET'])
def lista_inmuebles(request):
    inmuebles = Inmuebles.objects.all()
    serializer = InmueblesSerializer(inmuebles, many=True)
    return Response(serializer.data)
@api_view(['GET'])
def detalle_inmueble(request, pk):
    try:
        inmueble = Inmuebles.objects.get(pk=pk)
    except Inmuebles.DoesNotExist:
        return Response({'error': 'Inmueble no encontrado'}, status=404)

    serializer = InmueblesSerializer(inmueble)
    return Response(serializer.data)
@api_view(['POST'])
def crear_inmueble(request):
    serializer = InmueblesSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
@api_view(['PUT'])
def actualizar_inmueble(request, pk):
    try:
        inmueble = Inmuebles.objects.get(pk=pk)
    except Inmuebles.DoesNotExist:
        return Response({'error': 'Inmueble no encontrado'}, status=404)

    serializer = InmueblesSerializer(inmueble, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)

