from django.test import TestCase
from model_bakery import baker
from rest_framework.test import APIClient

from cashback.models import Vendedor
from cashback.utils import digito_mod11


class VendedorTests(TestCase):
    def setUp(self):
        self.cpf_magico = '15350946056'
        self.cpf_magico_formatado = '153.509.460-56'
        self.vendedor = baker.make('cashback.Vendedor')

    def test_nome_junta_first_name_e_last_name(self):
        first_name_e_last_name = self.vendedor.first_name + ' ' + self.vendedor.last_name
        self.assertEqual(self.vendedor.nome, first_name_e_last_name)

    def test_nome_atribui_first_name_e_last_name(self):
        first_name = 'Fulano'
        last_name = 'da Silva'
        nome = f'{first_name} {last_name}'
        vendedor = baker.make('cashback.Vendedor')
        vendedor.nome = nome
        self.assertEqual(vendedor.first_name, first_name)
        self.assertEqual(vendedor.last_name, last_name)

    def test_separar_nome_sobrenome_none_retorna_none_e_none(self):
        first, last = Vendedor.separar_nome_sobrenome(None)
        self.assertIsNone(first)
        self.assertIsNone(last)

    def test_separar_nome_sobrenome_apenas_um_nome(self):
        nome = 'Fulano'
        first, last = Vendedor.separar_nome_sobrenome(nome)
        self.assertEqual(first, nome)
        self.assertIsNone(last)

    def test_sanitizar_cpf_vazio_invalido(self):
        self.assertIsNone(Vendedor.sanitizar_cpf(None))

    def test_sanitizar_cpf_semnumeros_invalido(self):
        self.assertIsNone(Vendedor.sanitizar_cpf('qwertyuiop'))

    def test_sanitizar_cpf_poucos_numeros_invalido(self):
        self.assertIsNone(Vendedor.sanitizar_cpf('123'))

    def test_sanitizar_cpf_muitos_numeros_invalido(self):
        self.assertIsNone(Vendedor.sanitizar_cpf('123456789012'))

    def test_sanitizar_cpf_cpf_magico_valido(self):
        self.assertEqual(Vendedor.sanitizar_cpf(self.cpf_magico), self.cpf_magico)

    def test_sanitizar_cpf_invalido(self):
        cpf_invalido = '12345678912'
        self.assertIsNone(Vendedor.sanitizar_cpf(cpf_invalido))

    def test_sanitizar_cpf_cpf_magico_formatado_valido(self):
        self.assertEqual(Vendedor.sanitizar_cpf(self.cpf_magico_formatado), self.cpf_magico)

    def test_str_retorna_nome(self):
        self.assertEqual(str(self.vendedor), self.vendedor.nome)


class UtilsTests(TestCase):

    def test_digito_mod11_vazio_retorna_zero(self):
        self.assertEqual(digito_mod11([]), 0)

    def test_digito_mod11_cpf_magico(self):
        cpf_magico = [1, 5, 3, 5, 0, 9, 4, 6, 0, 5, 6]
        self.assertEqual(digito_mod11(cpf_magico[:9]), cpf_magico[9])
        self.assertEqual(digito_mod11(cpf_magico[:10]), cpf_magico[10])


class APITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.payload_vendedor = {"login": "dev", "nome": "Dev da Silva", "email": "dev@boticario.com.br", "senha": "dev@12345", "cpf": "15350946056"}

    def test_criar_vendedor_sucesso(self):
        response = self.client.post('/v1/vendedor/', self.payload_vendedor, format='json')
        self.assertEqual(response.status_code, 201)

    def test_criar_vendedor_sucesso_senha_escondida(self):
        response = self.client.post('/v1/vendedor/', self.payload_vendedor, format='json')
        data = response.json()
        self.assertEqual(data["senha"], "******")

    def test_criar_vendedor_em_branco_400(self):
        payload = {}
        response = self.client.post('/v1/vendedor/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_criar_vendedor_cpf_invalido(self):
        self.payload_vendedor["cpf"] = "123"
        response = self.client.post('/v1/vendedor/', self.payload_vendedor, format='json')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["cpf"], ["CPF 123 inválido"])

    def test_criar_vendedor_email_obrigatorio(self):
        del self.payload_vendedor["email"]
        response = self.client.post('/v1/vendedor/', self.payload_vendedor, format='json')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["email"], ["Este campo é obrigatório."])
