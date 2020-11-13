FROM python:3.8-alpine

RUN apk add musl-dev gcc
# Copia primeiro os arquivos que não vão ser muitos alterados durante o ciclo de vida do projeto
COPY entrypoint.sh /usr/app/entrypoint.sh
COPY requirements.txt /usr/app/requirements.txt

# Instala o requirements antes de copiar o código para evitar que mudanças no código forcem o pip a rodar novamente
RUN pip install -r /usr/app/requirements.txt

# Copia o código e configura do workdir
COPY src/ /usr/app/src/
WORKDIR /usr/app/src

ENTRYPOINT /usr/app/entrypoint.sh
