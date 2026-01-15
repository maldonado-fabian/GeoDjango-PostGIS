
import os
import zipfile
import tempfile
import geopandas as gpd
import pandas as pd
from shapely import wkb
from bs4 import BeautifulSoup
from django.contrib.gis.geos import GEOSGeometry
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.parsers import MultiPartParser
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

# Procesar KMZ View
class ProcesarKMZView(APIView):
    parser_classes = [MultiPartParser]
    
    def post(self, request):
        if 'archivo_kmz' not in request.FILES:
            return Response(
                {'error': 'No se proporcionó archivo KMZ'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        archivo_kmz = request.FILES['archivo_kmz']
        
        try:
            # Procesar el archivo KMZ
            new_df = self.procesar_kmz(archivo_kmz)
            
            # Insertar en la base de datos
            insertados = self.insertar_dataframe_en_bd(new_df)
            
            return Response({
                'mensaje': f'Procesados {len(new_df)} registros, insertados {insertados}',
                'total': len(new_df),
                'insertados': insertados
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def procesar_kmz(self, archivo_kmz):
        """Procesa igual que tu código con DataFrame"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Guardar archivo
            kmz_path = os.path.join(temp_dir, "archivo.kmz")
            with open(kmz_path, "wb") as f:
                for chunk in archivo_kmz.chunks():
                    f.write(chunk)
            
            # Extraer KMZ
            extraction_dir = os.path.join(temp_dir, "extracted_kml")
            with zipfile.ZipFile(kmz_path, "r") as kmz:
                kmz.extractall(extraction_dir)
            
            # Leer KML
            gdf = gpd.read_file(os.path.join(extraction_dir, "doc.kml"), driver='libkml')
            
            # Crear DataFrame igual que tu código
            new_df = pd.DataFrame(columns=['Rol_SII', 'direccion', 'predio_sii', 'mzs_sii', 'geometria'])
            
            for row in gdf.iterrows():
                rol_sii = row[1]['Name']
                soup = BeautifulSoup(row[1]['description'], 'html.parser')

                rows = soup.find_all('tr')
                # Extraer datos específicos
                direccion = soup.find('td', string='Direccion').find_next_sibling('td').string
                mzs_sii = soup.find('td', string='Mzs_SII').find_next_sibling('td').string.strip()
                prd_sii = soup.find('td', string='Prd_SII').find_next_sibling('td').string.strip()

                if rol_sii == f"{mzs_sii}-0{prd_sii[0:4]}":
                    new_df = pd.concat([new_df, pd.DataFrame({
                        'Rol_SII': [rol_sii],
                        'direccion': [direccion],
                        'predio_sii': [prd_sii],
                        'mzs_sii': [mzs_sii],
                        'geometria': [row[1]['geometry']]
                    })], ignore_index=True)
            
            new_df['geometria'] = new_df['geometria'].apply(
                lambda geom: wkb.loads(wkb.dumps(geom, output_dimension=2)) if geom else geom)
            return new_df
    
    def insertar_dataframe_en_bd(self, df):
        """Inserta DataFrame en la base de datos"""
        insertados = 0
        
        for _, row in df.iterrows():
            try:
                # Convertir geometría
                geometria = GEOSGeometry(row['geometria'].wkt) if row['geometria'] else None
                
                # Crear o actualizar
                Inmuebles.objects.update_or_create(
                    rol_sii=row['Rol_SII'],
                    defaults={
                        'manzana': row['mzs_sii'],
                        'predio': row['predio_sii'],
                        'direccion': row['direccion'],
                        'geom': geometria,
                        'region': 'Valparaiso'
                    }
                )
                insertados += 1
                
            except Exception as e:
                print(f"Error insertando {row['Rol_SII']}: {str(e)}")
                continue
        
        return insertados