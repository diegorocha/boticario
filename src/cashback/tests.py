from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils.timezone import now
from model_bakery import baker
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from cashback.api import ChoiceField
from cashback.models import Vendedor, Compra
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


class CompraTests(TestCase):
    def setUp(self):
        self.cpf_magico = '15350946056'
        self.compra = baker.make('cashback.Compra')

    def test_cashback_zero_sem_valor(self):
        self.compra.valor = 0
        self.assertEqual(self.compra.cashback, 0)

    def test_cashback_zero_sem_percentual(self):
        self.compra.percentual_cashback = 0
        self.assertEqual(self.compra.cashback, 0)

    def test_cachback_percentual_negativo(self):
        self.compra.percentual_cashback = -1
        with self.assertRaises(ValueError):
            _ = self.compra.cashback

    def test_cachback_percentual_maior_que_vinte(self):
        self.compra.percentual_cashback = 21
        with self.assertRaises(ValueError):
            _ = self.compra.cashback

    def test_cashback_calculado_corretamente(self):
        self.compra.valor = 200
        self.compra.percentual_cashback = 10
        self.assertAlmostEqual(self.compra.cashback, 20)

    def test_status_inicial_em_validacao(self):
        self.assertNotEqual(self.compra.vendedor.cpf, self.cpf_magico)
        self.assertEqual(self.compra.get_status_inicial(), "V")

    def test_status_inicial_cpf_magico(self):
        self.compra.vendedor.cpf = self.cpf_magico
        self.assertEqual(self.compra.get_status_inicial(), "A")

    def test_save_preenche_status(self):
        self.compra.status = None
        self.compra.save()
        self.assertIsNotNone(self.compra.status)

    def test_percentual_cashback_valor_negativo(self):
        valor = -1
        self.assertAlmostEqual(self.compra.get_percentual_cashback(valor), 0)

    def test_percentual_cashback_valor_1(self):
        valor = 1
        self.assertAlmostEqual(self.compra.get_percentual_cashback(valor), 10)

    def test_percentual_cashback_valor_999(self):
        valor = 999
        self.assertAlmostEqual(self.compra.get_percentual_cashback(valor), 10)

    def test_percentual_cashback_valor_1000(self):
        valor = 1000
        self.assertAlmostEqual(self.compra.get_percentual_cashback(valor), 15)

    def test_percentual_cashback_valor_1500(self):
        valor = 1500
        self.assertAlmostEqual(self.compra.get_percentual_cashback(valor), 15)

    def test_percentual_cashback_valor_1501(self):
        valor = 1501
        self.assertAlmostEqual(self.compra.get_percentual_cashback(valor), 20)

    def test_percentual_cashback_valor_99999(self):
        valor = 99999
        self.assertAlmostEqual(self.compra.get_percentual_cashback(valor), 20)

    def test_save_atualiza_cashback_ultimos_30_dias(self):
        cpf = "35770006005"
        trinta_e_um_dias = now() - timedelta(days=31)
        trinta_dias = now() - timedelta(days=30)

        vendedor = Vendedor.objects.create(cpf=cpf)

        # Essa compra não deve impactar no somatóro. % original é de 20%
        compra_trinta_e_um_dias = Compra.objects.create(codigo="123457", vendedor=vendedor, valor=Decimal(2000),
                                                        data=trinta_e_um_dias)

        # Essa compra deve impactar no somatório. % original é de 10%
        compra_trinta_dias = Compra.objects.create(codigo="123458", vendedor=vendedor, valor=Decimal(999),
                                                   data=trinta_dias)
        self.assertEqual(compra_trinta_dias.percentual_cashback, 10)

        # Com essa compra o novo percentual deve subir para 15%
        compra = Compra()
        compra.codigo = "123459"
        compra.vendedor = vendedor
        compra.data = now()
        compra.valor = Decimal(100)
        compra.save()
        self.assertEqual(compra.percentual_cashback, 15)

        # Essa compra não deve ter sido alterada
        compra_trinta_e_um_dias.refresh_from_db()
        self.assertEqual(compra_trinta_e_um_dias.percentual_cashback, 20)

        # Essa compra deve ter sido alterada para 15%
        compra_trinta_dias.refresh_from_db()
        self.assertEqual(compra_trinta_dias.percentual_cashback, 15)

    def test_save_atualiza_cashback_ultimos_30_dias_mesmo_vendedor(self):
        cpf = "35770006005"
        cpf_outro_vendedor = "87103564019"
        trinta_dias = now() - timedelta(days=30)

        vendedor = Vendedor.objects.create(cpf=cpf, username="vendedor")
        outro_vendedor = Vendedor.objects.create(cpf=cpf_outro_vendedor, username="outro-vendedor")

        # Essa compra não deve impactar no somatóro pois é de outro vendedor
        compra_outro_vendedor = Compra.objects.create(codigo="234567", vendedor=outro_vendedor, valor=Decimal(2000),
                                                      data=trinta_dias)

        # Essa compra deve impactar no somatório. % original é de 10%
        compra_trinta_dias = Compra.objects.create(codigo="234568", vendedor=vendedor, valor=Decimal(999),
                                                   data=trinta_dias)
        self.assertEqual(compra_trinta_dias.percentual_cashback, 10)

        # Com essa compra o novo percentual deve subir para 15%
        compra = Compra(codigo="234569", vendedor=vendedor, data=now(), valor=Decimal(100))
        compra.save()
        self.assertEqual(compra.percentual_cashback, 15)

        # Essa compra não deve ter sido alterada
        compra_outro_vendedor.refresh_from_db()
        self.assertEqual(compra_outro_vendedor.percentual_cashback, 20)

        # Essa compra deve ter sido alterada para 15%
        compra_trinta_dias.refresh_from_db()
        self.assertEqual(compra_trinta_dias.percentual_cashback, 15)


class UtilsTests(TestCase):

    def test_digito_mod11_vazio_retorna_zero(self):
        self.assertEqual(digito_mod11([]), 0)

    def test_digito_mod11_cpf_magico(self):
        cpf_magico = [1, 5, 3, 5, 0, 9, 4, 6, 0, 5, 6]
        self.assertEqual(digito_mod11(cpf_magico[:9]), cpf_magico[9])
        self.assertEqual(digito_mod11(cpf_magico[:10]), cpf_magico[10])


class ChoiceFieldTest(TestCase):
    def test_to_representation_allow_blank(self):
        field = ChoiceField(choices=(), allow_blank=True)
        self.assertEqual(field.to_representation(""), "")

    def test_to_representation_convert_to_value(self):
        key = 'foo'
        value = 'bar'
        choices = (
            (key, value)
        )
        field = ChoiceField(choices=choices)
        self.assertEqual(field.to_representation(value), value)


class APITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.payload_vendedor = {"login": "dev", "nome": "Dev da Silva", "email": "dev@boticario.com.br", "senha": "dev@12345", "cpf": "15350946056"}
        self.payload_compra = {"codigo": "123456", "valor": "100", "cpf": "15350946056"}

    def autenticate_client(self, client=None, cpf=None):
        if not cpf:
            cpf = self.payload_vendedor["cpf"]
        if not client:
            client = self.client

        vendedor = Vendedor.objects.filter(cpf=cpf).first()
        if not vendedor:
            vendedor = Vendedor.objects.create_user(username='Foo', email='foo@example.com', password='foo@bar',
                                                    cpf=cpf)
        refresh = RefreshToken.for_user(vendedor)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

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

    def test_login_vendedor_sucesso(self):
        login = "teste"
        senha = "senha@123"
        Vendedor.objects.create_user(username=login, password=senha)
        payload = {"login": login, "senha": senha}
        response = self.client.post('/v1/vendedor/login/', payload, format='json')
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", data)
        self.assertIn("refresh", data)

    def test_login_vendedor_incorreto(self):
        payload = {"login": "teste", "senha": "senha"}
        response = self.client.post('/v1/vendedor/login/', payload, format='json')
        data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual({'erro': 'Login ou senha incorretos'}, data)

    def test_login_vendedor_em_branco(self):
        response = self.client.post('/v1/vendedor/login/', {}, format='json')
        data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("login", data)
        self.assertIn("senha", data)

    def test_login_vendedor_refresh_token_sucesso(self):
        login = "token"
        senha = "senha@456"
        Vendedor.objects.create_user(username=login, password=senha)
        response = self.client.post('/v1/vendedor/login/', {"login": login, "senha": senha}, format='json')
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIn("refresh", data)
        refresh = data["refresh"]
        response = self.client.post('/v1/vendedor/refresh_token/', {"refresh": refresh}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", data)

    def test_login_vendedor_refresh_token_invalido(self):
        payload = {"refresh": "foo"}
        response = self.client.post('/v1/vendedor/refresh_token/', payload, format='json')
        data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual({"refresh": ["Token inválido"]}, data)

    def test_login_vendedor_refresh_sem_token(self):
        response = self.client.post('/v1/vendedor/refresh_token/', {}, format='json')
        data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual({"refresh": ["Este campo é obrigatório."]}, data)

    def test_compra_precisa_de_login(self):
        response = self.client.post('/v1/compra/')
        self.assertEqual(response.status_code, 401)

    def test_compra_options_autenticado(self):
        self.autenticate_client()
        response = self.client.options('/v1/compra/')
        self.assertEqual(response.status_code, 200)

    def test_compra__cpf_invalido(self):
        cpf_venda = '1234567891'
        self.autenticate_client()
        self.payload_compra['cpf'] = cpf_venda
        response = self.client.post('/v1/compra/', data=self.payload_compra, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"cpf": [f"CPF {cpf_venda} inválido"]})

    def test_compra_invalida_cpf_diferente(self):
        cpf_autenticado = '15350946056'
        cpf_venda = '67674926044'
        self.autenticate_client(cpf=cpf_autenticado)
        self.payload_compra['cpf'] = cpf_venda
        Vendedor.objects.create_user(username='test', email='test@example.com', password='test@123', cpf=cpf_venda)
        response = self.client.post('/v1/compra/', data=self.payload_compra, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"cpf": ["Não é permitido inserir uma compra para outro CPF"]})

    def test_compra__cpf_inexistente(self):
        cpf_autenticado = '15350946056'
        cpf_venda = '67674926044'
        self.autenticate_client(cpf=cpf_autenticado)
        self.payload_compra['cpf'] = cpf_venda
        response = self.client.post('/v1/compra/', data=self.payload_compra, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"cpf": [f"Objeto com cpf={cpf_venda} não existe."]})

    def test_compra__cpf_sanitizado(self):
        cpf_venda = '153.509.460-56'
        cpf_limpo = '15350946056'
        Vendedor.objects.create_user(username='Foo', email='foo@example.com', password='foo@bar',
                                     cpf=cpf_limpo)
        self.autenticate_client()
        self.payload_compra['cpf'] = cpf_venda
        response = self.client.post('/v1/compra/', data=self.payload_compra, format="json")
        data = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["cpf"], cpf_limpo)

    def test_compra_apenas_ultimos_30_dias_sucesso(self):
        self.autenticate_client()
        data = now() - timedelta(days=30)
        self.payload_compra["data"] = data.isoformat()
        response = self.client.post('/v1/compra/', data=self.payload_compra, format="json")
        data = response.json()
        self.assertEqual(response.status_code, 201)

    def test_compra_apenas_ultimos_30_dias_erro(self):
        self.autenticate_client()
        data = now() - timedelta(days=31)
        self.payload_compra["data"] = data.isoformat()
        response = self.client.post('/v1/compra/', data=self.payload_compra, format="json")
        data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data, {"data": ["Não é possível inserir uma compra de mais de 30 dias atrás"]})

    def test_compra_atualiza_cashback_ultimos_30_dias(self):
        """Apenas para ter uma versão integrada dessa mesma funcionalidade. Mas o teste do model já antende"""
        cpf = "35770006005"
        trinta_e_um_dias = now() - timedelta(days=31)
        trinta_dias = now() - timedelta(days=30)
        self.autenticate_client(cpf=cpf)
        vendedor = Vendedor.objects.filter(cpf=cpf).first()

        # Essa compra não deve impactar no somatóro. % original é de 20%
        compra_trinta_e_um_dias = Compra.objects.create(codigo="123457", vendedor=vendedor, valor=Decimal(2000), data=trinta_e_um_dias)

        # Essa compra deve impactar no somatório. % original é de 10%
        compra_trinta_dias = Compra.objects.create(codigo="123458", vendedor=vendedor, valor=Decimal(999), data=trinta_dias)
        self.assertEqual(compra_trinta_dias.percentual_cashback, 10)

        # Com essa compra o novo percentual deve subir para 15%
        payload = {
            "codigo": "123459",
            "cpf": cpf,
            "data": now().isoformat(),
            "valor": "100",
        }
        response = self.client.post('/v1/compra/', data=payload, format="json")
        data = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["percentual_cashback"], 15)

        # Essa compra não deve ter sido alterada
        compra_trinta_e_um_dias.refresh_from_db()
        self.assertEqual(compra_trinta_e_um_dias.percentual_cashback, 20)

        # Essa compra deve ter sido alterada para 15%
        compra_trinta_dias.refresh_from_db()
        self.assertEqual(compra_trinta_dias.percentual_cashback, 15)

    def test_compra_com_sucesso(self):
        self.autenticate_client()
        response = self.client.post('/v1/compra/', data=self.payload_compra, format="json")
        data = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertIn("codigo", data)
        self.assertIn("cpf", data)
        self.assertIn("data", data)
        self.assertIn("percentual_cashback", data)
        self.assertIn("cashback", data)
        self.assertIn("valor", data)
