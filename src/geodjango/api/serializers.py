from rest_framework import serializers
from .models import Amenazas, Clases, Evaluacion, Indicadores, Inmuebles, SubIndicadores

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
        fields = '__all__'
    
