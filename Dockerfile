FROM python:3.12-slim

ARG CODEX_NPM_PACKAGE=@openai/codex@0.115.0
ARG GEMINI_NPM_PACKAGE=@google/gemini-cli@latest

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        git \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g "${CODEX_NPM_PACKAGE}" "${GEMINI_NPM_PACKAGE}"

COPY pyproject.toml README.md /tmp/auto-dataset-build/
COPY src /tmp/auto-dataset-build/src

RUN python -m pip install --no-cache-dir /tmp/auto-dataset-build

WORKDIR /app

CMD ["/app/scripts/run-autonomous.sh"]
