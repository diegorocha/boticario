build:
	flake8 --ignore=E501
	python src/manage.py test
	docker build . -t boticario-backend-diego
	#docker push boticario-backend-diego  #  Push para um docker registry

ci-sample:
	docker build . -t boticario-backend-diego
	docker run --rm -d --name boticario-cashback-ci  boticario-backend-diego
	docker exec -it boticario-cashback-ci flake8 --ignore=E501
	docker exec -it boticario-cashback-ci python manage.py test
	#docker push boticario-backend-diego  #  Push para um docker registry
	docker stop boticario-cashback-ci

run: build
	docker run --rm -d -p 8080:8080 --name boticario-cashback  boticario-backend-diego

stop:
	docker stop boticario-cashback
