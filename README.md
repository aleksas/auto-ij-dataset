# auto-dataset

`auto-dataset` is a separate project incubated inside this repository. It is meant to move out into its own repository later.

Its job is narrow:

- build evaluation-ready investigative datasets with strong provenance
- turn public records into repeatable cases, answer keys, and rubrics
- give LLM agents a constrained loop for improving dataset coverage without loosening evidentiary discipline

This project sits between two existing layers:

- the current repository's investigative workflow, source-tier, and evidence rules
- the sibling retrieval stack in [`../investigative-journalism-ai-stack`](../investigative-journalism-ai-stack/README.md)

It does not replace either one. It produces the cases, manifests, and gold annotations needed to evaluate them.

## Why this exists

The strongest local note for this direction is [`../local-agent/docs/ideas/public-validation-and-gold-set-methodology.md`](../local-agent/docs/ideas/public-validation-and-gold-set-methodology.md). That note already defines the process for building a validation dataset:

- use structured public records where official fields are answer keys
- use public entity-link datasets where published links are partial ground truth
- use document collections with metadata for conversion and citation-grounding checks
- add a small manual gold set for journalist-style tasks such as follow-up quality and overclaim control

That same framing is repeated in:

- [`../local-agent/docs/ideas/journalistic-training-test-suite.md`](../local-agent/docs/ideas/journalistic-training-test-suite.md)
- [`../local-agent/grants/notes/nlnet-validation-methodology-2026-03-18.md`](../local-agent/grants/notes/nlnet-validation-methodology-2026-03-18.md)
- [`../local-agent/grants/notes/draft-ngi-workplan-attachment.md`](../local-agent/grants/notes/draft-ngi-workplan-attachment.md)

Local reference copies for this new project live in [`docs/references/README.md`](docs/references/README.md).

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
6. The suite should be able to feed both this repo's workflows and the sibling retrieval stack's retrieval-validation layer.

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

The bootstrap suite mirrors the current repo's own validation notes:

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
