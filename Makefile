DOCKER_IMAGE_NAME=test_db_image
DOCKER_CONTAINER_NAME=test_db_container
DB_PORT=5432

install:
	pip install -r requirements.txt

imbalances:
	python -m src.imbalances_script

daemon:
	python -m src.daemon

test_db:
	docker build -t $(DOCKER_IMAGE_NAME) -f Dockerfile.test_db .
	docker run -d --name $(DOCKER_CONTAINER_NAME) -p $(DB_PORT):$(DB_PORT) $(DOCKER_IMAGE_NAME)

stop_test_db:
	docker stop $(DOCKER_CONTAINER_NAME) || true
	docker rm $(DOCKER_CONTAINER_NAME) || true
	docker rmi $(DOCKER_IMAGE_NAME) || true

.PHONY: install imbalances daemon test_db run_test_db stop_test_db clean
