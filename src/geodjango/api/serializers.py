from rest_framework import serializers
from .models import Amenazas

class AmenazasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenazas
        fields = '__all__'