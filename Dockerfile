FROM python:3.10-alpine as builder

ENV POETRY_VERSION 1.4.2

RUN apk --no-cache add gcc musl-dev libffi-dev
RUN pip install --prefer-binary "poetry==$POETRY_VERSION"

WORKDIR /app
COPY pyproject.toml poetry.lock .
COPY leaf_desease_predictor ./leaf_desease_predictor

RUN poetry config virtualenvs.in-project true && \
    poetry install --only=main --no-root && \
    poetry build

FROM python:3.10-alpine
WORKDIR /app
COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/dist/*.whl .
COPY docker-entrypoint.sh config.yaml .

RUN ./.venv/bin/pip install *.whl && rm -rf *.whl
CMD ["./docker-entrypoint.sh"]
