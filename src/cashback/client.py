import logging
from decimal import Decimal
from urllib.parse import urljoin

from django.conf import settings
from requests import session

logger = logging.getLogger('core')


class SaldoAPI:

    def __init__(self):
        self.session = session()
        self.base_url = settings.SALDO_API
        self.session.headers = {
            "token": settings.SALDO_API_TOKEN,
        }

    def get_saldo(self, cpf):
        url = urljoin(self.base_url, f'/v1/cashback?cpf={cpf}')
        response = self.session.get(url)
        logger.debug("Consulta ao SaldoAPI", extra={
            "method": response.request.method,
            "url": response.request.url,
            "status": response.status_code,
            "body": response.content if response.status_code >= 400 else "-",
            "duration": response.elapsed.total_seconds()
        })
        if not response.ok:
            logger.error("Resposta inválida do SaldoAPI", extra={
                "status": response.status_code
            })
            return None
        data = response.json()
        data_status_code = data.get("statusCode")
        if data_status_code != 200:
            logger.error("SaldoAPI retornou um JSON inválido", extra={
                "statusCode": data_status_code
            })
            return None
        credit = data["body"]["credit"]
        return Decimal(credit / 100)
