from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Amenazas
from .serializers import AmenazasSerializer


# Create your views here.
@api_view(['GET'])
def lista_amenazas(request):
    amenazas = Amenazas.objects.all()
    serializer = AmenazasSerializer(amenazas, many=True)
    return Response(serializer.data)
