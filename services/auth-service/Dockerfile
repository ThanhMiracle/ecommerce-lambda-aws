# syntax=docker/dockerfile:1.6
ARG TARGETPLATFORM=linux/amd64

############################
# 1) Builder: build wheels (Lambda-compatible)
############################
FROM --platform=$TARGETPLATFORM public.ecr.aws/sam/build-python3.11 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Copy requirements first for cache efficiency
COPY services/auth-service/requirements.txt ./requirements.txt

# Build ALL wheels into /wheels (includes bcrypt)
RUN --mount=type=cache,target=/root/.cache/pip \
    set -eux; \
    pip install --upgrade pip setuptools wheel; \
    pip wheel --wheel-dir /wheels --prefer-binary -r ./requirements.txt; \
    echo "== builder wheels =="; \
    ls -lah /wheels; \
    # Fail fast if bcrypt wheel missing
    ls -lah /wheels | grep -i bcrypt

############################
# 2) Lambda Runtime
############################
FROM --platform=$TARGETPLATFORM public.ecr.aws/lambda/python:3.11 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/var/task

WORKDIR /var/task

COPY --from=builder /wheels /wheels
COPY services/auth-service/requirements.txt ./requirements.txt

RUN set -eux; \
    echo "== runtime wheels =="; \
    ls -lah /wheels | sed -n '1,200p'; \
    ls -lah /wheels | grep -i bcrypt; \
    pip install --no-index --find-links=/wheels -r ./requirements.txt; \
    rm -rf /wheels /root/.cache/pip

COPY services/auth-service/app ./app
COPY services/shared ./shared

CMD ["app.lambda_handler.handler"]