# Foundations

This subproject is grounded in five source strands.

For portability, local copies and adaptations of the most relevant source notes now live in [`references/README.md`](references/README.md).

## 1. Current repo validation notes

The clearest local process note is [`../../local-agent/docs/ideas/public-validation-and-gold-set-methodology.md`](../../local-agent/docs/ideas/public-validation-and-gold-set-methodology.md).

It defines four answer-key families:

- structured-record answer keys
- known-relationship answer keys
- metadata-backed document answer keys
- manual gold annotations

The related note [`../../local-agent/docs/ideas/journalistic-training-test-suite.md`](../../local-agent/docs/ideas/journalistic-training-test-suite.md) adds the case-based investigative angle:

- suspicious-pattern detection
- restraint against overclaiming
- provenance discipline
- next-step usefulness

## 2. Grants notes

The same validation story is restated in:

- [`../../local-agent/grants/notes/nlnet-validation-methodology-2026-03-18.md`](../../local-agent/grants/notes/nlnet-validation-methodology-2026-03-18.md)
- [`../../local-agent/grants/notes/draft-ngi-workplan-attachment.md`](../../local-agent/grants/notes/draft-ngi-workplan-attachment.md)

These notes are useful because they turn the idea into milestone language:

- public source families first
- partial ground truth where possible
- small manual gold set where exact keys do not exist
- explicit degradation testing between stronger online models and weaker local ones

## 3. Autonomous loop idea

[`../../local-agent/docs/ideas/autonomous-investigation-loop.md`](../../local-agent/docs/ideas/autonomous-investigation-loop.md) is the right local interpretation of `autoresearch`.

The important transfer is:

- small mutable surface
- fixed harness
- hard run budget
- result logging
- cheap revert path

For `auto-dataset`, that means the agent should mostly mutate cases, manifests, and rubrics, not invent new orchestration layers on every pass.

## 4. Separate eval packaging

`poemswe/co-researcher` is relevant less for its academic domain and more for its evaluation packaging:

- a separate `evals/` tree
- explicit test cases
- explicit rubrics
- a runner
- durable benchmark artifacts

This project uses the same separation idea, but for investigative-public-record workflows.

## 5. Sibling retrieval stack

The grants notes describe a sibling repo as the retrieval and indexing substrate. In this workspace that is most likely [`../../investigative-journalism-ai-stack/README.md`](../../investigative-journalism-ai-stack/README.md).

Relevant observations:

- the sibling stack already handles ingestion, indexing, and retrieval validation
- this repo already handles source-tier rules, evidence chains, and investigative workflow discipline
- `auto-dataset` should bridge them by producing evaluation-ready cases, answer keys, and gold annotations

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
