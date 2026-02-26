# syntax=docker/dockerfile:1.6
ARG TARGETPLATFORM=linux/amd64

FROM --platform=$TARGETPLATFORM public.ecr.aws/sam/build-python3.11 AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build

COPY services/order-service/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    set -eux; \
    pip install --upgrade pip setuptools wheel; \
    pip wheel --wheel-dir /wheels --prefer-binary -r ./requirements.txt

FROM --platform=$TARGETPLATFORM public.ecr.aws/lambda/python:3.11 AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 PYTHONPATH=/var/task
WORKDIR /var/task

COPY --from=builder /wheels /wheels
COPY services/order-service/requirements.txt ./requirements.txt

RUN set -eux; \
    pip install --no-index --find-links=/wheels -r ./requirements.txt; \
    rm -rf /wheels /root/.cache/pip

COPY services/order-service/app ./app
COPY services/shared ./shared

CMD ["app.lambda_handler.handler"]