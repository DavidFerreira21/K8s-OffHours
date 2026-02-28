IMAGE ?= k8s-offhours:local
KIND_CLUSTER ?= kind

.PHONY: build
build:
	docker build -t $(IMAGE) .

.PHONY: build-local
build-local:
	docker build -t k8s-offhours:local .

.PHONY: set-image
set-image:
	find k8s/base -name 'cronjob-*.yaml' -type f -exec sed -i "s|^\\([[:space:]]*image:[[:space:]]*\\).*|\\1$(IMAGE)|" {} +

.PHONY: kind-load
kind-load:
	kind load docker-image $(IMAGE) --name $(KIND_CLUSTER)

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
