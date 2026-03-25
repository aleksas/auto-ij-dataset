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
│       ├── source_artifacts/
│       ├── source_documents/
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

The checked-in suite mirrors the project's core methodology:

- structured public-record extraction
- entity-link recovery
- metadata-backed document grounding
- manual gold-set follow-up evaluation

See [`datasets/public-validation-v1/manifest.yaml`](datasets/public-validation-v1/manifest.yaml) and [`docs/foundations.md`](docs/foundations.md).

## Current suite status

The repository is past the template-only bootstrap stage. The current checked-in suite is in Phase 2, the first real public-suite stage.

- 65 cases total
- 60 validated cases and 5 templates
- 58 field-extraction cases, 4 entity-linking cases, 1 citation-grounding case, 1 coverage-comparison case, and 1 next-step-suggestion case
- 65 cases with checked-in source documents and 60 non-template cases with preserved upstream source snapshots
- explicit language metadata on every case and every source record
- current case-level source-language spread led by `en=37`, `fr=7`, `pl=3`, with long-tail coverage across `bg`, `cs`, `de`, `el`, `es`, `hr`, `it`, `lv`, `pt`, `ro`, `sk`, `sl`, and `sv`
- explicit source-family balance targets and a procurement dominance cap so weaker families are visible and prioritized

Lifecycle status vocabulary:

- `template`: scaffold or example case shape
- `harvested`: early case capture with enough structure to keep working and a checked-in source document, but raw upstream snapshots can still be deferred
- `draft`: real case under active refinement with the same lighter provenance contract as `harvested`
- `validated`: provenance-hardened case that passes the stronger checked-in artifact contract, including preserved raw upstream snapshots
- `gold_candidate`: review-ready benchmark candidate with candidate-preparation metadata, but not final manual signoff
- `gold`: manually reviewed benchmark case with explicit review metadata

That means case acquisition and provenance hardening are now separate stages. New cases can enter the suite as `harvested` or `draft` without immediately carrying raw upstream snapshots, while benchmark-intent cases should normally move through `validated` to `gold_candidate`, and only reach `gold` after human review capacity is available.

`gold_candidate` cases must carry `review_candidate` metadata:

- `prepared_by`
- `prepared_on`
- `rationale`

Language metadata vocabulary:

- `source_languages`: the language set that defines the case's upstream source coverage
- `evidence_languages`: the language set present in the checked-in evidence bundle
- `answer_language`: the language expected for the benchmark response
- `sources[].language`: the language of each individual source record

`cross_country_leak_reporting` cases are now required to carry at least two distinct source languages.

Source-family balance policy:

- `source_family_targets` define target ranges for each family
- the suite now treats `public_entity_link_dataset`, `public_documents_with_metadata`, `cross_country_leak_reporting`, and `journalist_style_case` as explicitly underrepresented families to prioritize
- `official_procurement` is capped by a configured max-share policy in the autonomous loop contract
- the dashboard and brief now surface overrepresented and underrepresented families directly

Warning: prose counts in narrative docs can drift. Use one of these live status surfaces before making planning decisions:

- `auto-dataset summary datasets/public-validation-v1/manifest.yaml` for machine-readable counts, gap analysis, lifecycle readiness, and run-log steering rollups
- `auto-dataset dashboard datasets/public-validation-v1/manifest.yaml` for a human-readable markdown dashboard
- [`docs/public-validation-v1-status.md`](docs/public-validation-v1-status.md) for the last checked-in dashboard snapshot

Status surface rules:

- `datasets/public-validation-v1/manifest.yaml` is the source of truth for the suite contract, targets, and loop budget
- `docs/roadmap.md` is the source of truth for phase narrative
- `auto-dataset summary` is the source of truth for machine-readable live counts, readiness state, and gap analysis
- the dashboard is the source of truth for human-readable live status and steering context

Regenerate the checked-in dashboard with:

```bash
PYTHONPATH=src python3 -m auto_dataset.cli dashboard \
  datasets/public-validation-v1/manifest.yaml \
  --output docs/public-validation-v1-status.md
```

## Unattended run mode

Use `auto-dataset brief <manifest>` before leaving an agent alone. The brief is derived from the manifest and prints:

- the timebox and run budget
- the active loop mode and its mode-specific rules
- the mutable and frozen surfaces
- the current coverage baseline
- the priority order for new case harvesting
- the failure policy for retryable versus nonretryable runs
- the keep/discard rules and required TSV log fields

The manifest is the source of truth for those details. `program.md` explains the operating principles, while the brief renders the current concrete budget, mode contract, and failure policy.

That keeps the dataset-building loop reviewable in the Karpathy sense: small mutable surface, fixed harness, hard budget, durable logs.

`auto-dataset summary` is now also the machine-readable steering surface. It reports:

- target-versus-actual progress for suite targets, source-family targets, and language targets
- lifecycle readiness, including which statuses are published and which statuses are considered evaluation-ready
- run-log rollups for acceptance rate, failure rate, change kinds, accepted versus rejected source families, and case-growth trends
- a `gap_analysis.recommended_next_actions` list for the next missing families, languages, and gold/lifecycle gaps, including whether to prepare `gold_candidate` cases or wait for reviewer signoff

## Autonomous Runner (Preferred)

The most reliable way to run the autonomous loop is via **Docker Compose**. This provides a fully isolated environment with Python 3.12, Node.js, and both Gemini and Codex CLIs pre-installed.

```bash
# Set your keys once
export HF_TOKEN=...
export GEMINI_API_KEY=...
# Optional: export OPENAI_API_KEY=...

# Start the autonomous loop
export AUTO_DATASET_UID=$(id -u)
export AUTO_DATASET_GID=$(id -g)
docker compose up --build auto-dataset-runner
```

The compose service:
- runs headless for `3600` seconds by default
- uses **Gemini 3 Flash Preview** (`gemini-3-flash-preview`) as the default agent
- falls back to Codex (`gpt-5.4`) if `GEMINI_API_KEY` is missing but `OPENAI_API_KEY` is present
- automatically handles validation, logging to `results/runs.tsv`, and publishing to Hugging Face
- preserves local file ownership on the host

To detach it and watch logs:
```bash
docker compose up -d --build auto-dataset-runner
docker compose logs -f auto-dataset-runner
```

## Manual Setup (Alternative)

If you prefer not to use Docker, ensure you have Python 3.11+, Node.js, and the necessary CLIs installed.

## Intermediate Publishing

The simplest publishing path is to build intermediate exports under ignored `artifacts/` and publish those snapshots to a public Hugging Face dataset repo.

```bash
export HF_TOKEN=...
auto-dataset export datasets/public-validation-v1/manifest.yaml
auto-dataset publish datasets/public-validation-v1/manifest.yaml --repo-name auto-ij-dataset
```

`auto-dataset publish` does three things:

- builds a fresh snapshot under `artifacts/hf-staging/<suite_id>/`
- materializes `source_documents/` from each case's `evidence_bundle.content_markdown` and copies declared local source artifacts, including preserved original PDFs, XML files, and HTML snapshots
- commits git changes in the repo unless `--skip-git-commit` is set
- pushes the current git branch to GitHub after a new commit
- publishes that snapshot as a new revision in the Hugging Face dataset repo

Every case now declares at least one repo-local source-document artifact under `evidence_bundle.artifacts`, typically under `datasets/public-validation-v1/source_documents/`. Exported snapshots carry those files forward alongside the case YAML and the materialized markdown source document.

`evidence_bundle.content_markdown` and `evidence_bundle.artifacts` are now required for every case, including templates, so new cases cannot be added without a dataset-carried source document and a repo-local artifact path.

The intended storage model is both local and published: keep source documents in the repo for offline validation, and publish the same files in the Hugging Face snapshot so downstream consumers get a self-contained dataset bundle.

Publishing is now lifecycle-aware:

- the manifest declares which statuses are included in published snapshots
- the current policy publishes the full working suite, including templates, any future `harvested` or `draft` cases, and any `gold_candidate` review queue
- downstream evaluation should default to `validated` and `gold` cases
- exports now carry both `summary.json` and `readiness.json`, and `source_documents/index.json` includes per-case lifecycle metadata such as status, pipeline stage, and evaluation-readiness flags

If reviewer time is unavailable, stop at `gold_candidate`. That keeps benchmark preparation moving without pretending unreviewed cases are final gold benchmarks.

For non-template cases, the repo now also preserves the original upstream source responses under `datasets/public-validation-v1/source_artifacts/`. In practice that means TED cases carry the downloaded XML/PDF/HTML snapshots used to build the markdown evidence, and Offshore Leaks cases carry saved HTML snapshots of the referenced pages.

Each artifact record should explain how to recover the upstream source, not just where the checked-in markdown lives. The required artifact fields now include:

- `source_url`
- `collected_at`
- `original_filename`
- `sha256`
- `acquisition_method`
- `license`
- `source_dataset`
- `notes`

If you want a fixed destination, pass `--repo-id <namespace>/<name>`. If you omit it, the command resolves the namespace from the Hugging Face token and uses `auto-ij-dataset` as the dataset repo name.

The intended unattended-loop contract is: accepted dataset changes should be pushed to GitHub, and intermediate dataset snapshots should be pushed to Hugging Face on the same cadence.
