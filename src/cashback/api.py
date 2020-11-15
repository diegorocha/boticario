from django.contrib.auth import authenticate
from rest_framework import mixins, status
from rest_framework import routers
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from cashback import models


class PasswordField(serializers.CharField):
    def to_representation(self, value):
        return '******'


class VendedorSerializer(serializers.ModelSerializer):
    login = serializers.CharField(source='username')
    nome = serializers.CharField()
    email = serializers.CharField(required=True)
    cpf = serializers.CharField(max_length=14)  # Para permitir CPF formatado (será tratado no model)
    senha = PasswordField(source='password')

    def create(self, validated_data):
        instance = super(VendedorSerializer, self).create(validated_data)
        # Corrige a criação da senha
        instance.set_password(validated_data["password"])
        instance.save()
        return instance

    def validate_cpf(self, value):
        cpf = models.Vendedor.sanitizar_cpf(value)
        if not cpf:
            raise serializers.ValidationError(f"CPF {value} inválido")
        return cpf

    class Meta:
        model = models.Vendedor
        fields = ['login', 'nome', 'cpf', 'email', 'senha']


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField(required=True)
    senha = serializers.CharField(required=True)


class VendedorViewset(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = models.Vendedor.objects.all()
    serializer_class = VendedorSerializer

    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        username = serializer.data['login']
        password = serializer.data['senha']
        user = authenticate(username=username, password=password)
        if not user:
            return Response({"erro": "Login ou senha incorretos"}, status=status.HTTP_400_BAD_REQUEST)
        tokens = RefreshToken.for_user(user)  # Gera os tokens JWT
        return Response(
            {
                'refresh': str(tokens),
                'access': str(tokens.access_token),
            },
            status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'])
    def refresh_token(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"refresh": ["Token inválido"]}, status=status.HTTP_400_BAD_REQUEST)


v1_router = routers.DefaultRouter()
v1_router.register('vendedor', VendedorViewset)
