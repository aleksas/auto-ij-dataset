# Foundations

This project is grounded in four design strands.

The supporting notes live in [`references/README.md`](references/README.md).

## 1. Public validation methodology

[`references/public-validation-methodology.md`](references/public-validation-methodology.md) defines the core answer-key families:

- structured-record answer keys
- known-relationship answer keys
- metadata-backed document answer keys
- manual gold annotations

Every case now includes an **inlined evidence bundle** (`content_markdown`) to support LLM training and offline evaluation, while maintaining explicit **provenance links** to the original public source for validation integrity. The checked-in suite also carries repo-local source-document files under `datasets/public-validation-v1/source_documents/`, linked from each case via `evidence_bundle.artifacts`, and intermediate exports materialize those bundles into `source_documents/` for downstream use. For non-template cases, the suite also preserves the original upstream responses under `datasets/public-validation-v1/source_artifacts/` so the repo and HF snapshot include both the markdownified evidence and the raw downloaded source files. Those artifact records now also capture recovery metadata such as source URL, collection date, original filename, digest, acquisition method, and source-dataset notes.

The suite now uses an explicit lifecycle vocabulary so case maturity is not hidden behind one generic `draft` bucket. In practice:

- `template` means scaffold only
- `harvested` means captured with a checked-in source document but not yet provenance-complete
- `draft` means actively being refined under the same lighter acquisition-stage contract
- `validated` means it passes the stronger local provenance contract, including preserved raw upstream snapshots
- `gold_candidate` means it is provenance-complete and review-ready, but still awaiting human signoff
- `gold` means it has manual review metadata and benchmark intent

This creates a deliberate three-stage path:

- acquisition stage: `harvested` and `draft`
- provenance-hardening stage: `validated`
- benchmark-queue stage: `gold_candidate`
- benchmark stage: `gold`

The project still requires every case to carry a checked-in source document, but only provenance-hardened statuses require preserved raw upstream snapshots.

Operationally, that means:

- a keepable `harvested` case must already have a real source trail, non-empty case structure, and a checked-in source-document artifact
- `content_markdown` may still be provisional at acquisition time, but it must exist so the dataset always carries materialized source text
- a case graduates to `validated` only after raw upstream snapshots, digests, and artifact metadata are present locally
- a case graduates to `gold_candidate` only after the provenance-complete record is paired with candidate-preparation metadata (`prepared_by`, `prepared_on`, `rationale`) for later human review
- a source that is temporarily unavailable should remain `harvested` or `draft` and be retried later rather than being promoted with missing raw evidence
- a source that cannot legally or practically be snapshotted should stay below `validated` unless the project later adds an explicit exception policy
- if reviewer capacity is unavailable, work should stop at `gold_candidate` rather than manufacturing unreviewed `gold` labels

The suite now also treats language coverage as first-class metadata:

- every case declares `source_languages`, `evidence_languages`, and `answer_language`
- every source record declares `language`
- multilingual reporting clusters must carry at least two distinct source languages

That makes it possible to track multilingual coverage structurally instead of inferring it from filenames, titles, or country names after the fact.

The suite also now carries explicit source-family balancing metadata:

- target ranges per source family
- a max-share cap for the dominant procurement slice
- an explicit list of weaker families to prioritize
- family-specific acquisition and preservation strategies

That turns source-family breadth into a tracked operating constraint instead of a vague preference in the manifest prose.

Phase 7 adds a clearer observability layer on top of that contract:

- `auto-dataset summary` now reports machine-readable gap analysis against suite, language, and source-family targets
- the summary also reports lifecycle readiness, including which statuses are published and which are evaluation-ready by default
- run-log reporting now includes accepted versus rejected source-family rollups, change-kind rollups, recent case-growth events, and a zero-growth-kept proxy for hardening/maintenance effort
- published snapshots now include `readiness.json`, and exported source-document indexes include per-case lifecycle/readiness metadata

## 2. Journalistic case design

[`references/journalistic-training-suite.md`](references/journalistic-training-suite.md) adds the case-based investigative angle:

- suspicious-pattern detection
- restraint against overclaiming
- provenance discipline
- next-step usefulness

The important operating implications are:

- public source families first
- partial ground truth where possible
- small manual gold set where exact keys do not exist
- explicit degradation testing between stronger online models and weaker local ones

## 3. Autonomous loop discipline

[`references/autonomous-loop.md`](references/autonomous-loop.md) captures the useful autonomous-loop constraint:

- small mutable surface
- fixed harness
- hard run budget
- result logging
- cheap revert path

For `auto-dataset`, that means the agent should mostly mutate cases, manifests, and rubrics, not invent new orchestration layers on every pass.

## 4. Boundaries and integration

[`references/system-boundaries.md`](references/system-boundaries.md) defines what this project should and should not own.

The main boundary is:

- this project defines cases, answer keys, rubrics, provenance, and exports
- other systems may consume those artifacts for retrieval, generation, or evaluation

## Working scope

`auto-dataset` should focus on:

- case harvesting and curation
- case manifests
- answer-key construction
- gold-set annotation scaffolds
- validation metadata

It should not try to become:

- a newsroom product
- a full retrieval stack
- a generic benchmark framework detached from investigative work
