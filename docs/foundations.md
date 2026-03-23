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
