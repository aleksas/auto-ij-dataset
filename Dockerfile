FROM python:3.12-slim

ARG CODEX_NPM_PACKAGE=@openai/codex@0.115.0

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        git \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g "${CODEX_NPM_PACKAGE}"

WORKDIR /app

CMD ["/app/scripts/run-autonomous.sh"]
