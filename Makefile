build:
	flake8 --ignore=E501
	python src/manage.py test
	docker build . -t boticario-backend-diego

run: build
	docker run --rm -d -p 8080:8080 --name boticario-cashback  boticario-backend-diego

stop:
	docker stop boticario-cashback
