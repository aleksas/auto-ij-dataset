#!/usr/bin/env bash

set -euo pipefail

: "${AUTO_DATASET_MANIFEST:=datasets/public-validation-v1/manifest.yaml}"
: "${AUTO_DATASET_MAX_RUNS:=1}"
: "${AUTO_DATASET_RUN_SECONDS:=3600}"
: "${AUTO_DATASET_WORKER_TIMEOUT_SECONDS:=900}"
: "${AUTO_DATASET_SLEEP_SECONDS:=10}"
: "${AUTO_DATASET_REPO_ID:=aleksasp/auto-ij-dataset}"
: "${AUTO_DATASET_GITHUB_TOKEN:=}"
: "${AUTO_DATASET_GIT_USER_NAME:=Aleksas Pielikis}"
: "${AUTO_DATASET_GIT_USER_EMAIL:=ant.kampo@gmail.com}"
: "${AUTO_DATASET_CODEX_MODEL:=gpt-5.4}"
: "${AUTO_DATASET_CODEX_REASONING_EFFORT:=medium}"
: "${AUTO_DATASET_CODEX_EXTRA_ARGS:=}"
: "${AUTO_DATASET_PUBLISH_EVERY:=1}"
: "${AUTO_DATASET_SKIP_PUBLISH:=0}"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "HF_TOKEN is required" >&2
  exit 1
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is required" >&2
  exit 1
fi

cd /app
mkdir -p artifacts

git -C /app config user.name "${AUTO_DATASET_GIT_USER_NAME}"
git -C /app config user.email "${AUTO_DATASET_GIT_USER_EMAIL}"
if [[ -n "${AUTO_DATASET_GITHUB_TOKEN}" ]]; then
  github_auth="$(printf 'x-access-token:%s' "${AUTO_DATASET_GITHUB_TOKEN}" | base64 | tr -d '\n')"
  git -C /app config http.https://github.com/.extraheader "AUTHORIZATION: basic ${github_auth}"
fi

worker_cmd="codex exec --dangerously-bypass-approvals-and-sandbox -C /app -m ${AUTO_DATASET_CODEX_MODEL}"
if codex exec --help 2>/dev/null | grep -q -- "--reasoning-effort"; then
  worker_cmd+=" --reasoning-effort ${AUTO_DATASET_CODEX_REASONING_EFFORT}"
else
  echo "codex exec does not support --reasoning-effort; continuing without it" >&2
fi
if [[ -n "${AUTO_DATASET_CODEX_EXTRA_ARGS}" ]]; then
  worker_cmd+=" ${AUTO_DATASET_CODEX_EXTRA_ARGS}"
fi
worker_cmd+=" -"

runner_args=(
  python
  -m
  auto_dataset.cli
  run
  "${AUTO_DATASET_MANIFEST}"
  --worker-cmd
  "${worker_cmd}"
  --max-runs
  "${AUTO_DATASET_MAX_RUNS}"
  --worker-timeout-seconds
  "${AUTO_DATASET_WORKER_TIMEOUT_SECONDS}"
  --sleep-seconds
  "${AUTO_DATASET_SLEEP_SECONDS}"
  --publish-every
  "${AUTO_DATASET_PUBLISH_EVERY}"
  --repo-id
  "${AUTO_DATASET_REPO_ID}"
)

if [[ "${AUTO_DATASET_SKIP_PUBLISH}" == "1" ]]; then
  runner_args+=(--skip-publish)
fi

if [[ "${AUTO_DATASET_RUN_SECONDS}" =~ ^[0-9]+$ ]] && (( AUTO_DATASET_RUN_SECONDS > 0 )); then
  set +e
  timeout "${AUTO_DATASET_RUN_SECONDS}s" "${runner_args[@]}"
  status=$?
  set -e
  if [[ ${status} -eq 124 ]]; then
    echo "Reached configured time limit of ${AUTO_DATASET_RUN_SECONDS}s"
    exit 0
  fi
  exit "${status}"
fi

exec "${runner_args[@]}"
