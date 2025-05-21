#!/bin/bash

poetry install --with migration && \
poetry run alembic upgrade head