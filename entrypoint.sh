#!/bin/sh

PORT=8080
WORKERS=4
THREADS=4

python manage.py migrate # Essa etapa pode ser executada em outro lugar (ci/pipeline), deixei aqui por praticidade
gunicorn boticario.wsgi --workers $WORKERS --threads $THREADS --worker-class eventlet --bind=0.0.0.0:$PORT
