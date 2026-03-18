# Autonomous Loop

This note copies the useful part of the local `autoresearch` interpretation and narrows it to dataset building.

## Transferable idea

The important lesson is not "let the agent run freely". It is:

- keep the mutable surface very small
- keep the evaluation harness fixed
- require each cycle to emit a result log
- define a hard keep or discard rule
- make revert cheap when a branch produces noise instead of signal

For `auto-dataset`, the mutable surface should mostly be:

- suite manifests
- case files
- rubrics
- source recipes

It should not mostly be:

- framework rewrites
- unconstrained orchestration changes
- speculative benchmark features disconnected from dataset quality

## Investigation analogue adapted for dataset building

Lock the core evidence contract:

- every case needs a source trail
- every case needs an explicit answer mode
- every case needs the right kind of answer key or rubric
- positive and negative cases both matter

Let the loop mutate:

- which source family is harvested next
- how cases are split across task types
- which official fields become answer keys
- which gold annotations are added to cover overclaim control and follow-up usefulness

## Scoring the loop

The loop should be scored on evidence and coverage gain, not narrative fluency.

Possible keep metrics:

- more source-grounded cases
- more complete answer keys
- more citation-grounding cases with precise locations
- more manual gold annotations for high-risk journalist-style tasks
- reduced ambiguity between `exact`, `rubric`, and `mixed` cases

## Safety stance

Treat early runs as harness-building and case-building work, not as publishable investigative output.

Start with:

- replayable public cases
- low-risk source families
- explicit logging in `results/runs.tsv`

Require human review before treating harvested cases as canonical.

## Why this matters for auto-dataset

This is the operational model for the project:

- bounded mutation
- fixed validation rules
- logged runs
- keep only the changes that improve dataset quality

## Source references

- `../../local-agent/docs/ideas/autonomous-investigation-loop.md`
- `https://github.com/karpathy/autoresearch`
