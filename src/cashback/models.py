from string import digits

from django.contrib.auth.models import AbstractUser
from django.db import models

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
