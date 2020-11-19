import logging

from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.views.generic.dates import timezone_today
from rest_framework import mixins, status, permissions, fields
from rest_framework import routers
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from cashback import models
from cashback.client import SaldoAPI

logger = logging.getLogger('core')


class PasswordField(serializers.CharField):
    def to_representation(self, value):
        return '******'


class ChoiceField(serializers.ChoiceField):
    def to_representation(self, obj):
        if obj == '' and self.allow_blank:
            return obj
        return self._choices[obj]


class ComprasPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class CPFRelatedField(serializers.SlugRelatedField):
    slug_field = 'cpf'

    def __init__(self, **kwargs):
        super(CPFRelatedField, self).__init__(slug_field=CPFRelatedField.slug_field, **kwargs)

    def run_validation(self, data=fields.empty):
        initial_value = data
        if isinstance(data, str):
            data = models.Vendedor.sanitizar_cpf(data)
            if not data:
                raise ValidationError(f"CPF {initial_value} inválido")
        return super(CPFRelatedField, self).run_validation(data=data)


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


class CompraSerializer(serializers.ModelSerializer):
    cpf = CPFRelatedField(queryset=models.Vendedor.objects.all(), source='vendedor')
    cashback = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    status = ChoiceField(models.Compra.STATUS_CHOICES, read_only=True)

    def get_user(self):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            return request.user

    def validate_cpf(self, value):
        user = self.get_user()
        if user.cpf != value.cpf:
            raise ValidationError("Não é permitido inserir uma compra para outro CPF")
        return value

    def validate_data(self, value):
        delta = timezone_today() - value.date()
        if delta.days > 30:
            raise ValidationError("Não é possível inserir uma compra de mais de 30 dias atrás")
        return value

    class Meta:
        model = models.Compra
        fields = ['codigo', 'valor', 'data', 'cpf', 'percentual_cashback', 'cashback', 'status']
        read_only_fields = ['percentual_cashback']


class VendedorViewset(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = models.Vendedor.objects.all()
    serializer_class = VendedorSerializer
    pagination_class = ComprasPagination

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
        update_last_login(None, user)
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
        except TokenError as ex:
            logger.exception(ex)
            return Response({"refresh": ["Token inválido"]}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def compras(self, request, pk):
        if request.user.cpf != pk:
            logger.info("Usuário tentou acessar listagem de vendas de outro vendedor",
                        extra={"cpf_usuario": request.user.cpf, "cpf_listagem": pk})
            return Response({"erro": "Não é possível acessar a listagem de vendas de outro vendedor"},
                            status.HTTP_400_BAD_REQUEST)

        # Vendedor precisa existir pois a rota exige autenticação
        vendedor = models.Vendedor.objects.filter(cpf=pk).first()
        page = self.paginate_queryset(vendedor.compras.order_by('-data'))
        serializer = CompraSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def saldo(self, request, pk):
        if request.user.cpf != pk:
            logger.info("Usuário tentou acessar saldo de cashback de outro vendedor",
                        extra={"cpf_usuario": request.user.cpf, "cpf_listagem": pk})
            return Response({"erro": "Não é possível acessar o saldo de outro vendedor"},
                            status.HTTP_400_BAD_REQUEST)
        saldo_api = SaldoAPI()
        saldo = saldo_api.get_saldo(pk)
        if not saldo:
            logger.error("Não foi possível obter o saldo", extra={"cpf": pk})
            return Response({}, status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"saldo": saldo}, status.HTTP_200_OK)


class CompraViewset(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = models.Compra.objects.all()
    serializer_class = CompraSerializer
    permission_classes = [permissions.IsAuthenticated]


v1_router = routers.DefaultRouter(trailing_slash=False)
v1_router.register('vendedor', VendedorViewset)
v1_router.register('compra', CompraViewset)
