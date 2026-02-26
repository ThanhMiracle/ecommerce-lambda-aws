# syntax=docker/dockerfile:1.6

############################
# 1) Builder Stage (wheels)
############################
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# copy only requirements first for caching
COPY notification-service/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    set -eux; \
    pip install --upgrade pip setuptools wheel; \
    pip wheel --wheel-dir /wheels --prefer-binary -r ./requirements.txt


############################
# 2) Lambda Runtime Stage
############################
FROM public.ecr.aws/lambda/python:3.11 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/var/task

WORKDIR /var/task

COPY --from=builder /wheels /wheels
COPY notification-service/requirements.txt ./requirements.txt

RUN set -eux; \
    pip install --no-index --find-links=/wheels -r ./requirements.txt; \
    rm -rf /wheels /root/.cache/pip

# app code
COPY notification-service/app ./app

# shared code (sibling in services/)
COPY shared ./shared

# Lambda handler function
CMD ["app.main.lambda_handler"]