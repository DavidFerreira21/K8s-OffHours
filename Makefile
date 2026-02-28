IMAGE ?= docker.io/davidferreira21/k8s-offhours:latest

.PHONY: build
build:
	docker build -t $(IMAGE) .

.PHONY: run-shutdown
run-shutdown:
	set -a; . ./.env; set +a; ACTION=shutdown python3 ./scripts/offhours.py

.PHONY: run-startup
run-startup:
	set -a; . ./.env; set +a; ACTION=startup python3 ./scripts/offhours.py

.PHONY: test
test:
	pytest -q

.PHONY: lint
lint:
	ruff check .
	ruff format --check .

.PHONY: deploy
deploy:
	kubectl apply -k k8s/base

.PHONY: uninstall
uninstall:
	kubectl delete -k k8s/base
