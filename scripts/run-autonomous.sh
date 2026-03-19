#!/usr/bin/env bash

set -euo pipefail

: "${AUTO_DATASET_MANIFEST:=datasets/public-validation-v1/manifest.yaml}"
: "${AUTO_DATASET_MAX_RUNS:=50}"
: "${AUTO_DATASET_RUN_SECONDS:=3600}"
: "${AUTO_DATASET_WORKER_TIMEOUT_SECONDS:=60}"
: "${AUTO_DATASET_SLEEP_SECONDS:=10}"
: "${AUTO_DATASET_REPO_ID:=aleksasp/auto-ij-dataset}"
: "${AUTO_DATASET_CODEX_MODEL:=gpt-5.2}"
: "${AUTO_DATASET_CODEX_EXTRA_ARGS:=}"
: "${AUTO_DATASET_PUBLISH_EVERY:=3}"
: "${AUTO_DATASET_SKIP_PUBLISH:=0}"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "HF_TOKEN is required" >&2
  exit 1
fi

cd /app
mkdir -p artifacts

git config --global --add safe.directory /app >/dev/null 2>&1 || true
python -m pip install -e /app

worker_cmd="codex exec --dangerously-bypass-approvals-and-sandbox -C /app -m ${AUTO_DATASET_CODEX_MODEL}"
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
