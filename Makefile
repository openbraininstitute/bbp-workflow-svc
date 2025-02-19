.PHONY: help python_build build_latest push_latest local_server

REGISTRY?=$(ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com
IMAGE_NAME?=bbp-workflow-svc

TAG ?= $(shell python3 -m setuptools_scm)

define HELPTEXT
Makefile usage
 Targets:
    python_build        Build, test and package python.
    docker_build_latest Build backend local docker image with the latest tag.
endef
export HELPTEXT

help:
	@echo "$$HELPTEXT"

python_build:
	pipx run build --sdist
	@echo "TAG: $(TAG)"

build_latest: python_build
	docker build -t $(IMAGE_NAME):$(TAG) . --platform=linux/amd64

push_latest: build_latest
	aws ecr get-login-password --region $(REGION) | docker login --username AWS --password-stdin $(REGISTRY)
	docker tag $(IMAGE_NAME):$(TAG) $(REGISTRY)/$(IMAGE_NAME):$(TAG)
	docker push $(REGISTRY)/$(IMAGE_NAME):$(TAG)
	docker logout $(REGISTRY)

local_server:
	docker run --network shared-network --name workflow-svc -it --rm -p 8100:8100 \
		-e DEBUG=True \
		-e USER=$$(whoami) \
		-e REDIRECT_URI=$$REDIRECT_URI \
		-e KC_HOST=$$KC_HOST \
		-e KC_REALM=$$KC_REALM \
		-e KC_SCR=$$KC_SCR \
		-e KC_SUB=$$KC_SUB \
		-e DB_API_URL=$$DB_API_URL \
		-e HPC_HEAD_NODE=$$HPC_HEAD_NODE \
		-e HPC_ENVIRONMENT=$$HPC_ENVIRONMENT \
		-e HPC_PATH_PREFIX=$$HPC_PATH_PREFIX \
		-e HPC_DATA_PREFIX=$$HPC_DATA_PREFIX \
		-e HPC_SIF_PREFIX=$$HPC_SIF_PREFIX \
		-e HPC_RESOURCE_PROVISIONER_API_URL=$$HPC_RESOURCE_PROVISIONER_API_URL \
		-e AWS_ACCESS_KEY_ID=$$AWS_ACCESS_KEY_ID \
                -e AWS_SECRET_ACCESS_KEY=$$AWS_SECRET_ACCESS_KEY \
		-e AWS_DEFAULT_REGION=$$AWS_DEFAULT_REGION \
		-e VIRTUAL_LAB_ID=$$VIRTUAL_LAB_ID \
		-e "PROJECT_ID"=$$PROJECT_ID \
		$(IMAGE_NAME):$(TAG) --platform=linux/amd64
