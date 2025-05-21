FROM --platform=$BUILDPLATFORM python:3.12-bookworm

WORKDIR /app

COPY pyproject.toml poetry.lock ./

ENV PYTHONPATH=./
ENV PYTHONUNBUFFERED=True

ARG DOCKER_TAG
ARG IMAGE
ARG REPO
ARG BUILDPLATFORM
ENV APP_VERSION=$DOCKER_TAG
ENV IMAGE=$IMAGE
ENV BUILDPLATFORM=$BUILDPLATFORM

RUN echo "Building Docker image $IMAGE:$APP_VERSION for $BUILDPLATFORM"

RUN apt-get update && \
    apt-get install -y --no-install-recommends

RUN rm -rf /var/lib/apt/lists/*

RUN python -m ensurepip --upgrade && \
    pip install --upgrade pip

RUN pip install poetry

RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

COPY . .

CMD ["poetry", "run", "python", "-m", "src.main"]
