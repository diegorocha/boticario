from datetime import timedelta
from decimal import Decimal
from string import digits

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Sum
from django.utils.timezone import now
from django.views.generic.dates import timezone_today

from cashback.utils import digito_mod11


class Vendedor(AbstractUser):
    # AbstractUser já possui first_name, last_name, e-mail e password
    cpf = models.CharField('CPF', max_length=11, blank=False, null=False, unique=True)

    @staticmethod
    def separar_nome_sobrenome(nome):
        first = None
        last = None
        if nome:
            nomes = nome.split(' ')
            if nomes:
                if len(nomes) == 1:
                    first = nome
                else:
                    first = nomes[0]
                    last = ' '.join(nomes[1:])
        return first, last

    @property
    def nome(self):
        return f'{self.first_name} {self.last_name}'

    @nome.setter
    def nome(self, value):
        self.first_name, self.last_name = self.separar_nome_sobrenome(value)

    @staticmethod
    def sanitizar_cpf(cpf):
        """
        Valida o CPF pelo tamanho e digito e retorna o CPF limpo de formatação se for valido.
        Retorna None se CPF for inválido
        :param cpf: CPF a ser validado
        :return: string or None
        """

        if not cpf:
            return None  # CPF é inválido, pois é vazio
        # Remove qualquer caractere não numérico e converte para int
        algarismos = list(map(int, filter(lambda c: c in digits, cpf)))

        if len(algarismos) != 11:
            return None  # CPF é inválido, pois não tem 11 caracteres

        cpf_calculado = algarismos[:9]
        # Gera o digito e verifica com a posicao 9 e 10 do array algarismos
        for i in range(9, 11):
            digito = digito_mod11(cpf_calculado)
            cpf_calculado.append(digito)
            if digito != algarismos[i]:
                return None  # CPF é inválido, pois um digito não confere
        return ''.join(map(str, cpf_calculado))  # CPF é válido

    def __str__(self):
        return self.nome


class Compra(models.Model):
    codigo = models.CharField("Código", max_length=6, null=False, blank=False, unique=True)
    valor = models.DecimalField("Valor", max_digits=8, decimal_places=2, null=False, blank=False)
    data = models.DateTimeField("Data", null=True, blank=True, default=now)
    vendedor = models.ForeignKey(Vendedor, null=False, blank=False, on_delete=models.PROTECT, related_name='compras')
    STATUS_CHOICES = (
        ('V', 'Em Validação'),
        ('A', 'Aprovado'),
        ('N', 'Negado')
    )
    status = models.CharField("Status", max_length=1, null=False, blank=False, choices=STATUS_CHOICES)
    percentual_cashback = models.FloatField("Percentual Cashback", null=False, blank=True)

    @property
    def cashback(self):
        if self.valor and self.percentual_cashback:
            if self.percentual_cashback < 0 or self.percentual_cashback > 20:
                raise ValueError("O percentual de cashback inválido")
            return self.valor * Decimal(self.percentual_cashback / 100)
        return 0.0

    def get_status_inicial(self):
        if self.vendedor and self.vendedor.cpf == '15350946056':
            return 'A'
        return 'V'

    @staticmethod
    def get_percentual_cashback(valor):
        if valor and valor > 0:
            if valor < 1000:
                return 10.0
            if valor <= 1500:
                return 15.0
            if valor > 1500:
                return 20.0
        return 0.0

    def save(self, **kwargs):
        # Preenche os atributos sem preenchimento do usuário
        if not self.status:
            self.status = self.get_status_inicial()

        # Precisa preencher pois o campo é NOT_NULL, mas será sobrescrito depois
        self.percentual_cashback = self.get_percentual_cashback(self.valor)

        # Salva a compra no banco de dados
        super(Compra, self).save(**kwargs)

        # Recalcula o total de vendas do último mês
        inicio = timezone_today() - timedelta(days=30)
        vendas_do_mes = self.vendedor.compras.filter(data__date__gte=inicio)

        sum = vendas_do_mes.aggregate(vendas_do_mes=Sum("valor"))
        if sum:
            novo_percentual = self.get_percentual_cashback(sum["vendas_do_mes"])
            # Atualiza o mesmo queryset para o novo percentual
            vendas_do_mes.update(percentual_cashback=novo_percentual)
            self.percentual_cashback = novo_percentual

    def __str__(self):
        return f"Compra {self.codigo}"
