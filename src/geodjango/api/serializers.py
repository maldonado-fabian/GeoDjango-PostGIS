from rest_framework import serializers
from .models import Amenazas, Clases, Evaluacion, Indicadores, Inmuebles, SubIndicadores
from django.contrib.gis.geos import GEOSGeometry

class AmenazasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenazas
        fields = '__all__'

class ClasesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clases
        fields = '__all__'

class EvaluacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluacion
        fields = '__all__'

class IndicadoresSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicadores
        fields = '__all__'

class SubIndicadoresSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubIndicadores
        fields = '__all__'

class InmueblesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inmuebles
        fields = ['id', 'manzana', 'predio', 'rol_sii', 'direccion', 'geom', 'region']
    
class EvaluacionDetalleSerializer(serializers.ModelSerializer):
    sub_indicador_nombre = serializers.CharField(source='id_subindicador.nombre', read_only=True)

    class Meta:
        model = Evaluacion
        fields = ['id', 'id_subindicador', 'sub_indicador_nombre', 'valor', 'fecha_evaluacion']

class InmueblesUpdateSerializer(serializers.ModelSerializer):
    """Limited serializer for editor partial updates (excludes geom and rol_sii)."""
    class Meta:
        model = Inmuebles
        fields = ['id', 'direccion', 'region', 'manzana', 'predio']
        read_only_fields = ['id']

class EvaluacionLoteItemSerializer(serializers.Serializer):
    id_subindicador = serializers.IntegerField()
    valor = serializers.IntegerField(min_value=1, max_value=4)


class EvaluacionLoteSerializer(serializers.Serializer):
    """Evaluación completa de un inmueble para una amenaza, en una sola request.

    Se exige el roster completo de sub-indicadores de la amenaza (validado en
    la vista, contra el mismo filtro que usa `lista_subindicadores`): una
    evaluación parcial haría que el inmueble se viera "evaluado" en el mapa
    con un índice de riesgo artificialmente bajo.
    """

    amenaza_id = serializers.IntegerField(min_value=1)
    evaluaciones = EvaluacionLoteItemSerializer(many=True, allow_empty=False)


class ReporteConfigSerializer(serializers.Serializer):
    """Parámetros de generación del informe PDF.

    Un solo informe por amenaza: el único parámetro es cuál.
    """

    amenaza_id = serializers.IntegerField(min_value=1)


class RiesgoConteoSerializer(serializers.Serializer):
    nivel_riesgo = serializers.CharField()
    cantidad = serializers.IntegerField()
    color = serializers.CharField(required=False)
    riesgo_promedio = serializers.FloatField(required=False)