from rest_framework import serializers
from .models import Amenazas, Clases, Evaluacion, Indicadores, Inmuebles, SubIndicadores
from django.contrib.gis.geos import GEOSGeometry

# `reports.config` sólo importa dataclasses: no arrastra matplotlib ni pandas al
# proceso web. El registro de secciones sí es pesado, y por eso se importa
# dentro de los validadores y no aquí.
from .reports.config import MODO_EJECUTIVO, MODOS

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

class ReporteConfigSerializer(serializers.Serializer):
    """Parámetros de generación del informe PDF.

    Valida contra el registro de secciones, para que pedir una sección
    inexistente devuelva 400 y no un PDF silenciosamente incompleto.
    """

    amenaza_id = serializers.IntegerField(min_value=1)
    modo = serializers.ChoiceField(choices=MODOS, default=MODO_EJECUTIVO)
    secciones = serializers.ListField(child=serializers.CharField(), required=False)
    excluir = serializers.ListField(child=serializers.CharField(), required=False)
    incluir_indice = serializers.BooleanField(required=False)
    basemap = serializers.BooleanField(required=False)

    def validate_secciones(self, valor):
        return self._validar_ids(valor)

    def validate_excluir(self, valor):
        return self._validar_ids(valor)

    def _validar_ids(self, valor):
        from .reports import sections
        desconocidas = sorted(set(valor) - set(sections.REGISTRY))
        if desconocidas:
            raise serializers.ValidationError(
                f'Secciones desconocidas: {", ".join(desconocidas)}. '
                f'Disponibles: {", ".join(sorted(sections.REGISTRY))}'
            )
        return valor


class RiesgoConteoSerializer(serializers.Serializer):
    nivel_riesgo = serializers.CharField()
    cantidad = serializers.IntegerField()
    color = serializers.CharField(required=False)
    riesgo_promedio = serializers.FloatField(required=False)