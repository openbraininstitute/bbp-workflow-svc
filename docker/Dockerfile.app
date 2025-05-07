# syntax=docker/dockerfile:1.9
ARG UV_VERSION=0.6.3
ARG PYTHON_VERSION=3.12
ARG PYTHON_BASE=${PYTHON_VERSION}-slim

# uv stage
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

###################################################
# build stage
###################################################

FROM python:$PYTHON_BASE AS builder
SHELL ["bash", "-e", "-x", "-o", "pipefail", "-c"]

RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    curl \
    rsync \
    ssh \
    git
EOT

# Copy uv from the uv stage
COPY --from=uv /uv /usr/local/bin/uv

# Enable bytecode compilation of sources after installing them
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Compile Python source files to bytecode after installation.
ENV UV_COMPILE_BYTECODE=1

# Do not allow python downloads
ENV UV_PYTHON_DOWNLOADS=never

# Set uv python
ENV UV_PYTHON=python${PYTHON_VERSION}

WORKDIR /code

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

###################################################
# run stage
###################################################

FROM python:$PYTHON_BASE
SHELL ["bash", "-e", "-x", "-o", "pipefail", "-c"]

RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    curl \
    rsync \
    ssh
EOT

WORKDIR /code

# Copy the installed packages from the builder stage
COPY --from=builder /code/.venv/ .venv/

# Add the code directory to PYTHONPATH so Python can find the modules
ENV PYTHONPATH="/code:$PYTHONPATH"

# Place executables in the environment at the front of the path
ENV PATH="/code/.venv/bin:$PATH"

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY src/app app/
COPY luigi.cfg /etc/luigi/luigi.cfg
COPY logging.cfg ./

ENV HOME=/code/workflow

# force compile python files to ensure they are available
# in cases where the container is readonly
RUN python -m compileall .

ARG ENVIRONMENT
ARG APP_NAME
ARG APP_VERSION
ARG COMMIT_SHA
ENV ENVIRONMENT=${ENVIRONMENT}
ENV APP_NAME=${APP_NAME}
ENV APP_VERSION=${APP_VERSION}
ENV COMMIT_SHA=${COMMIT_SHA}

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

CMD ["python", "-m", "app", "--host", "0.0.0.0", "--port", "8100"]
