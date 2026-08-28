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
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from .permissions import IsEditor
from . import riesgo
from .models import Amenazas, Clases, Evaluacion, Indicadores, Inmuebles, SubIndicadores
from .serializers import (
    AmenazasSerializer, ClasesSerializer, EvaluacionSerializer, EvaluacionDetalleSerializer,
    IndicadoresSerializer, InmueblesSerializer, InmueblesUpdateSerializer,
    SubIndicadoresSerializer,
)
from django.conf import settings
from sqlalchemy import create_engine
from django.http import HttpResponse
from dotenv import load_dotenv
load_dotenv()


# ── Auth ──────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    role = 'editor' if (user.is_superuser or user.groups.filter(name='editor').exists()) else 'viewer'
    return Response({'username': user.username, 'role': role})


# ── Amenaza activa ────────────────────────────────────────────────────────────

# Escala del índice de riesgo. Definida en api/riesgo.py, que es la fuente única
# de verdad; se replica en src/mapa/main.js y la paridad la verifica un test.
RIESGO_MAX = riesgo.ESCALA_MAX

# Amenaza por omisión cuando la petición no la indica: Incendio, la única que
# existía antes de que la plataforma fuera multi-amenaza.
AMENAZA_POR_DEFECTO = 1


def amenaza_id_de(request, default=None):
    """Lee `?amenaza_id=` de la query string. `default` si no viene."""
    bruto = request.query_params.get('amenaza_id')
    if bruto in (None, ''):
        return default
    try:
        return int(bruto)
    except (TypeError, ValueError):
        raise ValidationError({'amenaza_id': 'Debe ser un entero.'})


def nombre_amenaza(amenaza_id):
    """Nombre de la amenaza, para titular exportaciones. '' si no existe."""
    return Amenazas.objects.filter(pk=amenaza_id).values_list('nombre', flat=True).first() or ''


# ── Amenazas ──────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lista_amenazas(request):
    amenazas = Amenazas.objects.all()
    serializer = AmenazasSerializer(amenazas, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_amenaza(request, pk):
    try:
        amenaza = Amenazas.objects.get(pk=pk)
    except Amenazas.DoesNotExist:
        return Response({'error': 'Amenaza no encontrada'}, status=404)
    serializer = AmenazasSerializer(amenaza)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsEditor])
def crear_amenaza(request):
    serializer = AmenazasSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['PUT'])
@permission_classes([IsEditor])
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


# ── Clases ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lista_clases(request):
    clases = Clases.objects.all()
    amenaza_id = amenaza_id_de(request)
    if amenaza_id is not None:
        clases = clases.filter(sub_indicador__indicador__amenaza_id=amenaza_id)
    serializer = ClasesSerializer(clases, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_clase(request, pk):
    try:
        clase = Clases.objects.get(pk=pk)
    except Clases.DoesNotExist:
        return Response({'error': 'Clase no encontrada'}, status=404)
    serializer = ClasesSerializer(clase)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsEditor])
def crear_clase(request):
    serializer = ClasesSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsEditor])
def actualizar_clase(request, pk):
    try:
        clase = Clases.objects.get(pk=pk)
    except Clases.DoesNotExist:
        return Response({'error': 'Clase no encontrada'}, status=404)
    serializer = ClasesSerializer(clase, data=request.data, partial=request.method == 'PATCH')
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


# ── Evaluacion ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lista_evaluaciones(request):
    qs = Evaluacion.objects.all()
    id_inmueble = request.query_params.get('id_inmueble')
    if id_inmueble:
        qs = qs.filter(id_inmueble=id_inmueble)
    serializer = EvaluacionSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lista_evaluaciones_inmueble(request, pk):
    evaluaciones = Evaluacion.objects.filter(id_inmueble=pk).select_related('id_subindicador')
    # Sin este filtro la ficha del mapa mezclaría los sub-indicadores de todas
    # las amenazas evaluadas para el inmueble.
    amenaza_id = amenaza_id_de(request)
    if amenaza_id is not None:
        evaluaciones = evaluaciones.filter(id_subindicador__indicador__amenaza_id=amenaza_id)
    serializer = EvaluacionDetalleSerializer(evaluaciones, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_evaluacion(request, pk):
    try:
        evaluacion = Evaluacion.objects.get(pk=pk)
    except Evaluacion.DoesNotExist:
        return Response({'error': 'Evaluacion no encontrada'}, status=404)
    serializer = EvaluacionSerializer(evaluacion)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsEditor])
def crear_evaluacion(request):
    serializer = EvaluacionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsEditor])
def actualizar_evaluacion(request, pk):
    try:
        evaluacion = Evaluacion.objects.get(pk=pk)
    except Evaluacion.DoesNotExist:
        return Response({'error': 'Evaluacion no encontrada'}, status=404)
    serializer = EvaluacionSerializer(evaluacion, data=request.data, partial=request.method == 'PATCH')
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


# ── Indicadores ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lista_indicadores(request):
    indicadores = Indicadores.objects.all()
    amenaza_id = amenaza_id_de(request)
    if amenaza_id is not None:
        indicadores = indicadores.filter(amenaza_id=amenaza_id)
    serializer = IndicadoresSerializer(indicadores, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_indicador(request, pk):
    try:
        indicador = Indicadores.objects.get(pk=pk)
    except Indicadores.DoesNotExist:
        return Response({'error': 'Indicador no encontrado'}, status=404)
    serializer = IndicadoresSerializer(indicador)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsEditor])
def crear_indicador(request):
    serializer = IndicadoresSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['PUT'])
@permission_classes([IsEditor])
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


# ── SubIndicadores ────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lista_subindicadores(request):
    subindicadores = SubIndicadores.objects.all()
    amenaza_id = amenaza_id_de(request)
    if amenaza_id is not None:
        subindicadores = subindicadores.filter(indicador__amenaza_id=amenaza_id)
    serializer = SubIndicadoresSerializer(subindicadores, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_subindicador(request, pk):
    try:
        subindicador = SubIndicadores.objects.get(pk=pk)
    except SubIndicadores.DoesNotExist:
        return Response({'error': 'SubIndicador no encontrado'}, status=404)
    serializer = SubIndicadoresSerializer(subindicador)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsEditor])
def crear_subindicador(request):
    serializer = SubIndicadoresSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['PUT'])
@permission_classes([IsEditor])
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


# ── Inmuebles ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lista_inmuebles(request):
    inmuebles = Inmuebles.objects.all()
    serializer = InmueblesSerializer(inmuebles, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_inmueble(request, pk):
    try:
        inmueble = Inmuebles.objects.get(pk=pk)
    except Inmuebles.DoesNotExist:
        return Response({'error': 'Inmueble no encontrado'}, status=404)
    serializer = InmueblesSerializer(inmueble)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsEditor])
def crear_inmueble(request):
    serializer = InmueblesSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsEditor])
def actualizar_inmueble(request, pk):
    try:
        inmueble = Inmuebles.objects.get(pk=pk)
    except Inmuebles.DoesNotExist:
        return Response({'error': 'Inmueble no encontrado'}, status=404)

    if request.method == 'PATCH':
        # Only allow editing metadata fields, not geometry or identifier
        serializer = InmueblesUpdateSerializer(inmueble, data=request.data, partial=True)
    else:
        serializer = InmueblesSerializer(inmueble, data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


# ── Geospatial exports (editor-only write ops, read via GET) ──────────────────

def _engine():
    url = ("postgresql://" + os.getenv('DATABASE_USER') + ":" + os.getenv('DATABASE_PASSWORD')
           + "@" + os.getenv('DATABASE_HOST') + ":" + os.getenv('DATABASE_PORT')
           + "/" + os.getenv('DATABASE_NAME'))
    return create_engine(url)


def sql_indice_por_inmueble(amenaza_id):
    """Índice de riesgo total por inmueble para una amenaza, con su color de nivel.

    Lo comparten las exportaciones a SHP y a KML. `amenaza_id` se castea a int
    antes de interpolarse.
    """
    return f"""
        SELECT id_inmueble, direccion, rol_sii, SUM(total) as indice_de_riesgo, geom,
            {riesgo.case_sql('SUM(total)')} as symbol_color
        FROM (
            SELECT e.id_inmueble, i.geom, i.direccion, i.rol_sii, ind.id as indicador_id,
                   SUM(e.valor * si.peso) * ind.peso as total
            FROM evaluacion e
            JOIN sub_indicadores si ON e.id_subindicador = si.id
            JOIN indicadores ind ON si.indicador_id = ind.id
            JOIN inmuebles i ON e.id_inmueble = i.id
            WHERE ind.amenaza_id = {int(amenaza_id)}
            GROUP BY e.id_inmueble, ind.id, ind.peso, i.geom, i.direccion, i.rol_sii
        ) as subtotales
        GROUP BY id_inmueble, geom, direccion, rol_sii
        ORDER BY id_inmueble;
    """


class CrearSHPView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        con = _engine()
        amenaza_id = amenaza_id_de(request, AMENAZA_POR_DEFECTO)

        gdf = gpd.read_postgis(sql_indice_por_inmueble(amenaza_id), con)

        with tempfile.TemporaryDirectory() as temp_dir:
            base_name = nombre_amenaza(amenaza_id).replace(' ', '_') or 'Riesgo'
            shp_path = os.path.join(temp_dir, f"{base_name}.shp")
            gdf.to_file(shp_path, driver='ESRI Shapefile', encoding='utf-8')

            zip_path = os.path.join(temp_dir, f"{base_name}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
                    file_path = os.path.join(temp_dir, f"{base_name}{file_ext}")
                    if os.path.exists(file_path):
                        zipf.write(file_path, f"{base_name}{file_ext}")

            with open(zip_path, 'rb') as zip_file:
                response = HttpResponse(zip_file.read(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="{base_name}.zip"'
                return response


class ProcesarKMZView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsEditor]

    def post(self, request):
        if 'archivo_kmz' not in request.FILES:
            return Response(
                {'error': 'No se proporcionó archivo KMZ'},
                status=status.HTTP_400_BAD_REQUEST
            )

        archivo_kmz = request.FILES['archivo_kmz']

        try:
            new_df = self.procesar_kmz(archivo_kmz)
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
        with tempfile.TemporaryDirectory() as temp_dir:
            kmz_path = os.path.join(temp_dir, "archivo.kmz")
            with open(kmz_path, "wb") as f:
                for chunk in archivo_kmz.chunks():
                    f.write(chunk)

            extraction_dir = os.path.join(temp_dir, "extracted_kml")
            with zipfile.ZipFile(kmz_path, "r") as kmz:
                kmz.extractall(extraction_dir)

            gdf = gpd.read_file(os.path.join(extraction_dir, "doc.kml"), driver='libkml')

            new_df = pd.DataFrame(columns=['Rol_SII', 'direccion', 'predio_sii', 'mzs_sii', 'geometria'])

            for row in gdf.iterrows():
                rol_sii = row[1]['Name']
                soup = BeautifulSoup(row[1]['description'], 'html.parser')
                rows = soup.find_all('tr')
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
        insertados = 0
        for _, row in df.iterrows():
            try:
                geometria = GEOSGeometry(row['geometria'].wkt) if row['geometria'] else None
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


class CrearKMLView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import simplekml
        from shapely.geometry import Point, Polygon, MultiPolygon

        con = _engine()
        amenaza_id = amenaza_id_de(request, AMENAZA_POR_DEFECTO)
        amenaza = nombre_amenaza(amenaza_id)

        gdf = gpd.read_postgis(sql_indice_por_inmueble(amenaza_id), con, geom_col='geom')
        gdf = gdf.to_crs(epsg=4326)

        kml = simplekml.Kml()

        def hex_to_kml_color(hex_color):
            hex_color = hex_color.lstrip('#')
            r = hex_color[0:2]
            g = hex_color[2:4]
            b = hex_color[4:6]
            return f'ff{b}{g}{r}'

        for _, row in gdf.iterrows():
            geom = row['geom']
            color = hex_to_kml_color(row['symbol_color'])
            indice = row['indice_de_riesgo']
            fill_pct = min(round(indice / RIESGO_MAX * 100), 100)
            nivel = riesgo.nivel_por_indice(indice).label

            description = f"""
            <div style="font-family:Arial,sans-serif;width:280px;">
              <div style="background:{row['symbol_color']};padding:10px 14px;border-radius:6px 6px 0 0;">
                <div style="font-size:11px;color:rgba(255,255,255,0.8);text-transform:uppercase;letter-spacing:1px;">Riesgo de {amenaza}</div>
                <div style="font-size:17px;font-weight:bold;color:white;margin-top:2px;">Inmueble #{row['id_inmueble']}</div>
                <div style="display:inline-block;background:rgba(255,255,255,0.25);color:white;padding:2px 10px;border-radius:10px;font-size:12px;margin-top:4px;">{nivel}</div>
              </div>
              <div style="background:#fafafa;padding:12px 14px;border:1px solid #e0e0e0;border-top:none;border-radius:0 0 6px 6px;">
                <table style="width:100%;border-collapse:collapse;font-size:13px;">
                  <tr>
                    <td style="color:#888;padding:4px 0;width:90px;">Dirección</td>
                    <td style="font-weight:bold;padding:4px 0;">{row['direccion']}</td>
                  </tr>
                  <tr>
                    <td style="color:#888;padding:4px 0;">Rol SII</td>
                    <td style="padding:4px 0;">{row['rol_sii']}</td>
                  </tr>
                </table>
                <div style="margin-top:10px;padding-top:10px;border-top:1px solid #eee;">
                  <table style="width:100%;">
                    <tr>
                      <td style="font-size:12px;color:#555;">Índice de Riesgo</td>
                      <td style="font-size:14px;font-weight:bold;text-align:right;color:{row['symbol_color']};">{round(indice, 2)} / {RIESGO_MAX}</td>
                    </tr>
                  </table>
                  <div style="background:#e0e0e0;border-radius:4px;height:8px;margin-top:6px;">
                    <div style="background:{row['symbol_color']};width:{fill_pct}%;height:8px;border-radius:4px;"></div>
                  </div>
                </div>
              </div>
            </div>
            """

            if isinstance(geom, Point):
                pnt = kml.newpoint(name=str(row['id_inmueble']), coords=[(geom.x, geom.y)])
                pnt.description = description
                pnt.style.iconstyle.color = color
            elif isinstance(geom, (Polygon, MultiPolygon)):
                polys = [geom] if isinstance(geom, Polygon) else geom.geoms
                for poly in polys:
                    pol = kml.newpolygon(
                        name=str(row['id_inmueble']),
                        outerboundaryis=list(poly.exterior.coords)
                    )
                    pol.description = description
                    pol.style.polystyle.color = color
                    pol.style.linestyle.color = 'ff888888'
                    pol.style.linestyle.width = 1

        with tempfile.NamedTemporaryFile(delete=False, suffix=".kml") as tmp:
            kml.save(tmp.name)
            with open(tmp.name, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/vnd.google-earth.kml+xml')
                nombre = amenaza.replace(' ', '_') or 'Riesgo'
                response['Content-Disposition'] = f'attachment; filename="{nombre}.kml"'
                return response


class CrearKMLDetalleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import json
        import simplekml
        from datetime import datetime
        from shapely.geometry import Point, Polygon, MultiPolygon

        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M')

        con = _engine()
        amenaza_id = amenaza_id_de(request, AMENAZA_POR_DEFECTO)
        amenaza = nombre_amenaza(amenaza_id)

        sql = f"""
        SELECT id, geom, direccion, rol_sii, manzana, predio, detalle_riesgo
        FROM postgisftw.detalle_calculo({int(amenaza_id)})
        """

        gdf = gpd.read_postgis(sql, con, geom_col='geom')
        gdf = gdf.to_crs(epsg=4326)

        def hex_to_kml_color(hex_color):
            h = hex_color.lstrip('#')
            return f'ff{h[4:6]}{h[2:4]}{h[0:2]}'

        kml = simplekml.Kml()
        kml.document.name = f'Riesgo de {amenaza}'
        kml.document.description = f'Datos actualizados por ultima vez {timestamp}'

        for _, row in gdf.iterrows():
            geom = row['geom']
            detalle = row['detalle_riesgo']
            if isinstance(detalle, str):
                detalle = json.loads(detalle)

            indicadores = detalle.get('indicadores') or []
            total_riesgo = sum((ind.get('riesgo_indicador') or 0) for ind in indicadores)
            nivel_riesgo = riesgo.nivel_por_indice(total_riesgo)
            hex_color = nivel_riesgo.color
            kml_color = hex_to_kml_color(hex_color)
            nivel = nivel_riesgo.label
            fill_pct = min(round(total_riesgo / RIESGO_MAX * 100), 100)
            value_color = nivel_riesgo.color_texto

            # Pick header text colors based on background luminance
            _h = hex_color.lstrip('#')
            _r, _g, _b = int(_h[0:2], 16), int(_h[2:4], 16), int(_h[4:6], 16)
            _lum = (0.299 * _r + 0.587 * _g + 0.114 * _b) / 255
            if _lum > 0.45:
                text_color = '#1a1a1a'
                text_color_dim = 'rgba(0,0,0,0.6)'
                badge_bg = 'rgba(0,0,0,0.15)'
            else:
                text_color = '#ffffff'
                text_color_dim = 'rgba(255,255,255,0.8)'
                badge_bg = 'rgba(255,255,255,0.25)'

            indicadores_html = ''.join(
                f'<tr>'
                f'<td style="padding:3px 0;font-size:11px;color:#444;">{ind.get("indicador_nombre","")}</td>'
                f'<td style="padding:3px 0;font-size:11px;font-weight:bold;text-align:right;color:{value_color};">{round(ind.get("riesgo_indicador") or 0, 2)}</td>'
                f'</tr>'
                for ind in indicadores
            )

            description = (
                f'<div style="font-family:Arial,sans-serif;width:250px;height:300px;box-sizing:border-box;overflow:hidden;">'
                f'<div style="background:{hex_color};padding:8px 10px;">'
                f'<div style="font-size:9px;color:{text_color_dim};text-transform:uppercase;letter-spacing:1px;">Riesgo de {amenaza}</div>'
                f'<div style="font-size:13px;font-weight:bold;color:{text_color};margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{row["direccion"]}</div>'
                f'<div style="font-size:10px;color:{text_color_dim};margin-top:1px;">Rol SII: {row["rol_sii"]}</div>'
                f'<div style="display:inline-block;background:{badge_bg};color:{text_color};padding:1px 8px;border-radius:8px;font-size:10px;margin-top:4px;">{nivel}</div>'
                f'</div>'
                f'<div style="background:#fafafa;padding:8px 10px;border:1px solid #e0e0e0;border-top:none;">'
                f'<table style="width:100%;margin-bottom:6px;"><tr>'
                f'<td style="font-size:10px;color:#555;">Índice de Riesgo Total</td>'
                f'<td style="font-size:14px;font-weight:bold;text-align:right;color:{value_color};">{round(total_riesgo,2)}<span style="font-size:10px;color:#999;"> / {RIESGO_MAX}</span></td>'
                f'</tr></table>'
                f'<div style="background:#e0e0e0;border-radius:3px;height:6px;margin-bottom:8px;">'
                f'<div style="background:{hex_color};width:{fill_pct}%;height:6px;border-radius:3px;"></div></div>'
                f'<div style="font-size:10px;font-weight:bold;color:#333;margin-bottom:4px;border-bottom:1px solid #eee;padding-bottom:3px;">Indicadores</div>'
                f'<table style="width:100%;border-collapse:collapse;">{indicadores_html}</table>'
                f'<div style="margin-top:8px;padding-top:6px;border-top:1px solid #eee;">'
                f'<div style="font-size:9px;color:#aaa;">Datos actualizados por ultima vez {timestamp}</div>'
                f'<div style="text-align:right;margin-top:2px;">'
                f'<a href="http://localhost:5173/" style="font-size:11px;color:#1a73e8;text-decoration:none;">Ver más detalle &rsaquo;</a>'
                f'</div></div>'
                f'</div></div>'
            )

            if isinstance(geom, Point):
                pnt = kml.newpoint(name=str(row['id']), coords=[(geom.x, geom.y)])
                pnt.description = description
                pnt.style.iconstyle.color = kml_color
            elif isinstance(geom, (Polygon, MultiPolygon)):
                polys = [geom] if isinstance(geom, Polygon) else geom.geoms
                for poly in polys:
                    pol = kml.newpolygon(
                        name=str(row['id']),
                        outerboundaryis=list(poly.exterior.coords)
                    )
                    pol.description = description
                    pol.style.polystyle.color = kml_color
                    pol.style.linestyle.color = 'ff888888'
                    pol.style.linestyle.width = 1

        with tempfile.NamedTemporaryFile(delete=False, suffix=".kml") as tmp:
            kml.save(tmp.name)
            with open(tmp.name, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/vnd.google-earth.kml+xml')
                nombre = amenaza.replace(' ', '_') or 'Riesgo'
                response['Content-Disposition'] = f'attachment; filename="{nombre}_Detalle.kml"'
                return response


# ── Reporte PDF (resumen global) — generación asíncrona con Celery ────────────

from celery.result import AsyncResult
from django.http import FileResponse
from .tasks import generar_pdf_resumen_task


class GenerarPDFResumenView(APIView):
    """POST: encola la generación del PDF de resumen y devuelve el task_id."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amenaza_id = request.data.get('amenaza_id', 1)
        try:
            amenaza_id = int(amenaza_id)
        except (TypeError, ValueError):
            return Response({'error': 'amenaza_id inválido'}, status=status.HTTP_400_BAD_REQUEST)
        tarea = generar_pdf_resumen_task.delay(amenaza_id)
        return Response({'task_id': tarea.id, 'estado': 'PENDING'},
                        status=status.HTTP_202_ACCEPTED)


class EstadoPDFResumenView(APIView):
    """GET: estado de la tarea de generación del PDF."""
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        res = AsyncResult(task_id)
        data = {'task_id': task_id, 'estado': res.status}
        if res.failed():
            data['error'] = str(res.result)
        return Response(data)


class DescargarPDFResumenView(APIView):
    """GET: descarga el PDF generado cuando la tarea terminó."""
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        res = AsyncResult(task_id)
        if not res.successful():
            return Response({'estado': res.status, 'detalle': 'El PDF aún no está listo.'},
                            status=status.HTTP_409_CONFLICT)
        info = res.result or {}
        ruta = info.get('ruta')
        if not ruta or not os.path.exists(ruta):
            return Response({'error': 'Archivo no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(open(ruta, 'rb'), as_attachment=True,
                            filename=info.get('archivo', 'resumen_riesgo.pdf'),
                            content_type='application/pdf')
