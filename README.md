# Desafio Backend Boticário

## Sobre o projeto

Projeto desenvolvido para atender a seguinte [especificação](Especificacao.pdf)

## Como executar

Para executar o projeto via docker (docker e make são necessários):

```bash
make run
```

Para finalizar o container:

```bash
make stop
```

A imagem docker utiliza o [gunicorn](https://gunicorn.org/) como webserver rodando na porta `8080` (aceita requisição de qualquer origem)


Para executar localmente, recomendo a utilização de um [virtualenv](https://virtualenv.pypa.io/en/latest/)

Com o virtualenv ativo:

```bash
pip install -r requirements.txt
python src/manage.py migrate
python src/manage.py runserver
```

Localmente é utilizado o webserver de testes do django rodando na porta `8000` (apenas requisções do mesmo host)

## Decisões de arquitetura

Optei pelo Django e DjangoRestFramework pois são uma combinação muito produtiva para desenvolvimento de APIs com python.

Entretanto por não utilizar todas as funcionalidades do Django (templates, admin, middlewares etc) esse projeto poderia muito bem ser desenvolvido com `Flask` ou simular.

Utilizei o `sqlite3` como engine de banco de dados por ser prática para rodar (não precisa de instalação adicional de pacotes no sistema operacional), mas o Django suporta a maioria dos SGBDs do mercado, e a troca é simples e indolor.

Utilizei o [django-rest-framework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/getting_started.html#usage) como plugin para JWT

Adicionei log estruturado em JSON para melhor indexação em alguma solução mais robusta de logs como o [ELK](https://www.elastic.co/pt/what-is/elk-stack)

Inclui um `request_id` com intuito de vincular todos os logs gerados durante o tratamento da mesma requisição, isso facilitará a correlação dos logs futuramente.

Optei por incluir algumas regras de negócio complementares para facilitar o desenvolvimento:

* Validação do CPF segundo o algoritmo do dígito verificador
* Sanitização do CPF quando recebido com formatação
* Impedir a inclusão de vendas com mais de 30 dias
* Permitir a omissão do atributo data na criação da compra (utilizando a hora atual como valor default)
* Forçar o login via JWT em todas os endpoints (exceto a criação de vendedor)
* Impedir que um vendedor consiga fazer consultas relativas a outro vendedor

É relevante frisar, que interpretei o trecho `cashback do
valor vendido no período de um mês (sobre a soma de todas as vendas)` como uma janela rotativa de 30 dias, e ao inserir uma nova compra (sempre dentro dessa janela) o valor total de vendas é recalculado para ajuste do percentual, se for necessário.

Interpretei também que retorno da consulta de saldo de cashback é em centavos (prache no mercado), e por praticidade do usuário eu converti o valor reais realizando a divisão do mesmo por `100`

## Endpoints

### Cadastro de Vendedor

`POST /v1/vendedor/`

Rota para a inclusão de um novo vendedor

Exemplo de cURL

```
curl -XPOST http://localhost:8080/v1/vendedor/ -H "Content-Type: application/json" -d '{"login": "teste", "nome": "Teste da Silva", "cpf": "554.436.380-33", "email": "teste@boticario.com.br", "senha": "teste@123"}'
```

Retorna 201 em caso de sucesso

Retorna 400 caso algum dado seja inválido

Retorna 500 caso ocorra algum erro inesperado

### Validação de Login

Rota para obtenção dos tokens JWT para autenticação

`POST /v1/vendedor/login/`

Exemplo de cURL

```
curl -XPOST http://localhost:8080/v1/vendedor/login/ -H "Content-Type: application/json" -d '{"login": "teste", "senha": "teste@123"}'
```

Retorna 200 em caso de sucesso, com o seguinte JSON

```json
{
  "refresh": "...",
  "access": "..."
}
```

O atribuito `access` será necessário para autenticação nas rotas seguintes

O atributo `refresh` será necessário para renovação do `access` depois de 5 minutos.

Retorna 400 caso algum dado seja inválido

Retorna 500 caso ocorra algum erro inesperado

### Refresh token

Rota para renovação do token `access` da autenticação.

`POST /v1/vendedor/refresh_token/`

Exemplo de cURL

```
curl -XPOST http://localhost:8080/v1/vendedor/refresh_token/ -H "Content-Type: application/json" -d '{"refresh": "..."}'
```

Retorna 200 em caso de sucesso, com o seguinte JSON

```json
{
  "access": "..."
}
```
O novo valor de `access` deve ser utilizado na autentação das chamadas de agora em diante

Retorna 400 caso algum dado seja inválido

Retorna 500 caso ocorra algum erro inesperado

### Cadastro de Compra

Rota para a inclusão de uma venda do vendedor autenticado

`POST /v1/compra/`

Autenticação (via request header)

```
Authorization: Bearer {access}
```

Exemplo de cURL

```
curl -XPOST http://localhost:8080/v1/compra/ -H "Content-Type: application/json" -H "Authorization: Bearer [...]" -d '{"codigo": "234567", "valor": 100, "cpf": "554.436.380-33", "data": "2020-11-19T03:16:20"}'
```

Retorna 201 em caso de sucesso com o seguinte JSON

```json
{
  "codigo": "234567",
  "valor": "100.00",
  "data": "2020-11-19T03:16:20-03:00",
  "cpf": "55443638033",
  "percentual_cashback": 10,
  "cashback": "10.00",
  "status": "Em Validação"
}
```

Retorna 400 caso algum dado seja inválido

Retorna 401 em caso de falha na autenticação

Retorna 500 caso ocorra algum erro inesperado

### Listagem de Compras

Rota para listagem das vendas do vendedor

`GET /v1/vendedor/{cpf}/compras/`

Autenticação (via request header)

```
Authorization: Bearer {access}
```

Exemplo de cURL

```
curl -XGET http://localhost:8080/v1/vendedor/55443638033/compras/ -H "Authorization: Bearer [...]"
```

Retorna 200 em caso de sucesso com o seguinte JSON

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "codigo": "234567",
      "valor": "100.00",
      "data": "2020-11-19T03:16:20-03:00",
      "cpf": "55443638033",
      "percentual_cashback": 10,
      "cashback": "10.00",
      "status": "Em Validação"
    }
  ]
}
```

Essa rota contem uma paginação de até 10 compras por página.

O endereço da proxima página está no atributo `next`, bem como a pagina anterior em `previous`

A quantidade total de registros da consulta (e não da página) está no atributo `count`

E as compras em si estão no atributo `results`

Retorna 400 caso algum dado seja inválido

Retorna 401 em caso de falha na autenticação

Retorna 500 caso ocorra algum erro inesperado

### Saldo acumulado de Cashback

Rota para retorno do saldo total de cashback do vendedor

`GET /v1/vendedor/{cpf}/saldo/`

Autenticação (via request header)

```
Authorization: Bearer {access}
```

Exemplo de cURL

```
curl -XGET http://localhost:8080/v1/vendedor/55443638033/saldo/ -H "Authorization: Bearer [...]"
```

Retorna 200 em caso de sucesso com o seguinte JSON

```json
{
  "saldo": 34.08
}

```

Retorna 400 caso algum dado seja inválido

Retorna 401 em caso de falha na autenticação

Retorna 500 caso ocorra algum erro inesperado
