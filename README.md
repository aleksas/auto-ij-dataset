# auto-dataset

`auto-dataset` builds source-grounded validation datasets for investigative journalism and public-record research systems.

Its job is narrow:

- build evaluation-ready investigative datasets with strong provenance
- turn public records into repeatable cases, answer keys, and rubrics
- give LLM agents a constrained loop for improving dataset coverage without loosening evidentiary discipline

## Why this exists

Investigative workflows need more than raw corpora or prompt benchmarks. They need:

- task definitions
- explicit answer keys or rubrics
- preserved source provenance
- scoring that treats unsupported or overclaimed outputs as failures

This project starts from four practical case families:

- use structured public records where official fields are answer keys
- use public entity-link datasets where published links are partial ground truth
- use document collections with metadata for conversion and citation-grounding checks
- add a small manual gold set for journalist-style tasks such as follow-up quality and overclaim control

Supporting design notes live in [`docs/references/README.md`](docs/references/README.md).

## External design inspiration

- `karpathy/autoresearch`: small mutable surface, fixed validation harness, hard keep/discard loop, run logging
- `poemswe/co-researcher`: separate eval tree with test cases, rubrics, runner, and benchmark outputs

The point is not "fully autonomous journalism". The point is a bounded agent process that can grow a public validation suite while preserving source receipts and answer-key discipline.

This repo now makes that operating contract explicit in the suite manifest. A suite can declare its unattended run budget, mutable surface, coverage priorities, and required run-log columns, and `auto-dataset brief` renders that into an operator handoff.

## Project layout

```text
auto-dataset/
├── datasets/
│   └── public-validation-v1/
│       ├── cases/
│       └── manifest.yaml
├── docs/
├── results/
├── rubrics/
├── src/auto_dataset/
├── tests/
├── program.md
└── pyproject.toml
```

## Core ideas

1. The evaluation harness is fixed and easy to review.
2. The mutable surface is small: cases, manifests, rubrics, and source recipes.
3. Every case stays attached to a public source URL or a preserved local file.
4. Exact-answer tasks and rubric-scored tasks are separated explicitly.
5. Unsupported or overclaimed outputs count as failures.
6. The suite should be exportable into other evaluation or retrieval systems without changing its evidence contract.

## Bootstrap workflow

```bash
cd auto-dataset
python -m venv .venv
source .venv/bin/activate
pip install -e .
auto-dataset validate datasets/public-validation-v1/manifest.yaml
auto-dataset summary datasets/public-validation-v1/manifest.yaml
auto-dataset brief datasets/public-validation-v1/manifest.yaml
```

## Initial suite shape

The bootstrap suite mirrors the project's core methodology:

- structured public-record extraction
- entity-link recovery
- metadata-backed document grounding
- manual gold-set follow-up evaluation

See [`datasets/public-validation-v1/manifest.yaml`](datasets/public-validation-v1/manifest.yaml) and [`docs/foundations.md`](docs/foundations.md).

## Unattended run mode

Use `auto-dataset brief <manifest>` before leaving an agent alone. The brief is derived from the manifest and prints:

- the timebox and run budget
- the mutable and frozen surfaces
- the current coverage baseline
- the priority order for new case harvesting
- the keep/discard rules and required TSV log fields

The manifest is the source of truth for those details. `program.md` explains the operating principles, while the brief renders the current concrete budget and log contract.

That keeps the dataset-building loop reviewable in the Karpathy sense: small mutable surface, fixed harness, hard budget, durable logs.

## Autonomous Runner

`auto-dataset run` is the one-command orchestration entrypoint for unattended work. It does not bundle a model runtime; instead it drives an external worker command in a loop, validates after each cycle, appends to `results/runs.tsv`, and on publish cadence it commits and pushes git changes and publishes an intermediate Hugging Face snapshot.

```bash
export HF_TOKEN=...
auto-dataset run datasets/public-validation-v1/manifest.yaml \
  --worker-cmd 'your-agent-command' \
  --repo-id aleksasp/auto-ij-dataset
```

The worker command is executed by `/bin/bash -c`, receives the runner prompt on stdin, and also gets:

- `AUTO_DATASET_REPO_ROOT`
- `AUTO_DATASET_MANIFEST`
- `AUTO_DATASET_RUN_PROMPT_FILE`

If you want to drive it from Docker, the simplest shape is:

```bash
docker run --rm -it \
  --user "$(id -u):$(id -g)" \
  -e HF_TOKEN="$HF_TOKEN" \
  -v "$PWD":/app \
  -w /app \
  python:3.12-slim \
  bash -lc "apt-get update && apt-get install -y git && python -m pip install -e . && python -m auto_dataset.cli run datasets/public-validation-v1/manifest.yaml --worker-cmd 'your-agent-command' --repo-id aleksasp/auto-ij-dataset"
```

Using `--user "$(id -u):$(id -g)"` keeps `artifacts/` writable on the host after Docker-based runs and publishes.

For a repeatable headless setup, use the included container files instead of a long shell command:

```bash
export HF_TOKEN=...
export OPENAI_API_KEY=...
export AUTO_DATASET_UID=$(id -u)
export AUTO_DATASET_GID=$(id -g)
docker compose up --build auto-dataset-runner
```

The compose service runs headless for `3600` seconds by default, uses `50` max runs, and gives Codex full execution permissions inside the container via `codex exec --dangerously-bypass-approvals-and-sandbox`. To detach it, use:

```bash
docker compose up -d --build auto-dataset-runner
docker compose logs -f auto-dataset-runner
```

## Intermediate Publishing

The simplest publishing path is to build intermediate exports under ignored `artifacts/` and publish those snapshots to a public Hugging Face dataset repo.

```bash
export HF_TOKEN=...
auto-dataset export datasets/public-validation-v1/manifest.yaml
auto-dataset publish datasets/public-validation-v1/manifest.yaml --repo-name auto-ij-dataset
```

`auto-dataset publish` does three things:

- builds a fresh snapshot under `artifacts/hf-staging/<suite_id>/`
- commits tracked git changes if tracked files changed
- pushes the current git branch to GitHub after a new commit
- publishes that snapshot as a new revision in the Hugging Face dataset repo

If you want a fixed destination, pass `--repo-id <namespace>/<name>`. If you omit it, the command resolves the namespace from the Hugging Face token and uses `auto-ij-dataset` as the dataset repo name.

The intended unattended-loop contract is: accepted dataset changes should be pushed to GitHub, and intermediate dataset snapshots should be pushed to Hugging Face on the same cadence.
