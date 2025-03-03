SHELL := /bin/bash

export APP_NAME := workflow-svc
export COMMIT_SHA := $(shell git rev-parse HEAD)
export APP_VERSION := $(shell git describe --abbrev --dirty --always --tags)

define load_env
	$(eval ENV_FILE := .env.$(1))
	@echo "Loading env from $(ENV_FILE)"
	$(eval include $(ENV_FILE))
endef

install:  ## Install dependencies into .venv
	uv sync --no-install-project

compile-deps:  ## Create or update the lock file, without upgrading the version of the dependencies
	uv lock

upgrade-deps:  ## Create or update the lock file, using the latest version of the dependencies
	uv lock --upgrade

check-deps:  ## Check that the dependencies in the existing lock file are valid
	uv lock --locked

format:  ## Run formatters
	uv run -m ruff format
	uv run -m ruff check --fix

lint:  ## Run linters
	uv run -m ruff format --check
	uv run -m ruff check
	uv run -m mypy app auth

build:  ## Build the Docker image
	docker compose --progress=plain build app

run-docker: build  ## Run the application in Docker
	docker compose up app --watch --remove-orphans

test-local:  ## Run tests locally
	@$(call load_env,test-local)
	uv run -m pytest
	uv run -m coverage xml
	uv run -m coverage html
