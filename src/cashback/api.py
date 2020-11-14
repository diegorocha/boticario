from rest_framework import mixins
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework import routers

from cashback import models


class PasswordField(serializers.CharField):
    def to_representation(self, value):
        return '******'


class VendedorSerializer(serializers.ModelSerializer):
    login = serializers.CharField(source='username')
    nome = serializers.CharField()
    cpf = serializers.CharField(max_length=14)  # Para permitir CPF formatado (será tratado no model)
    senha = PasswordField(source='password')

    def validate_cpf(self, value):
        cpf = models.Vendedor.sanitizar_cpf(value)
        if not cpf:
            raise serializers.ValidationError(f"CPF {value} inválido")
        return cpf

    class Meta:
        model = models.Vendedor
        fields = ['login', 'nome', 'cpf', 'email', 'senha']


class VendedorViewset(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = models.Vendedor.objects.all()
    serializer_class = VendedorSerializer


v1_router = routers.DefaultRouter()
v1_router.register('vendedor', VendedorViewset)
