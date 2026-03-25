# auto-dataset program

This project borrows the useful constraint from `autoresearch`: the agent is not supposed to change everything.

## Objective

For one unattended week, grow a public, source-grounded validation suite for investigative-journalism systems.

The system should improve case coverage, answer keys, and rubrics without weakening provenance rules.

The exact run budget, source-family priority order, loop modes, failure policy, and run-log schema live in the target suite manifest. Treat the manifest as the source of truth, and use `auto-dataset brief <manifest>` to render the current operating contract before each unattended run.

The preferred unattended entrypoint is `docker compose up --build`. This uses the included `Dockerfile` and `docker-compose.yml` to provide a consistent, isolated environment with all dependencies (Python, Node.js, Gemini/Codex CLIs) pre-installed. It automatically handles the `auto-dataset run` loop, validation, logging, and publishing.

If running outside of Docker, use `auto-dataset run <manifest> --worker-cmd '...'`. The runner drives one worker cycle at a time, validates the suite, appends the run log, and performs git/Hugging Face sync on publish cadence. In that mode, the worker should stop after making one bounded batch and leave log/publish work to the runner. Use `--mode` when you need the runner to switch between acquisition, hardening, and gold-curation behavior; in practice, gold-curation should usually prepare `gold_candidate` cases and defer final `gold` promotion until human review is available.

## Fixed surfaces

Treat these as the evaluation harness and change them only with strong reason:

- `src/auto_dataset/validation.py`
- the manifest and case schema conventions
- the rule that every substantive case must point to a public source URL or preserved local record
- the rule that exact-answer tasks and rubric-scored tasks stay separated

## Mutable surfaces

The agent should spend most of its time here:

- `datasets/*/cases/*.yaml`
- `datasets/*/manifest.yaml`
- `rubrics/*.md`
- `docs/*.md`

## Loop

1. Read `README.md`, `program.md`, `docs/foundations.md`, and the target suite manifest.
2. Run `auto-dataset brief <manifest>` and follow the rendered operating contract.
3. Pick one source family and ship one bounded batch of cases.
4. Run `auto-dataset validate <manifest>`.
5. Run `auto-dataset summary <manifest>` and inspect target gaps, lifecycle readiness, and run-log steering signals before deciding to keep the batch.
6. In manual mode, append a structured line to `results/runs.tsv`.
7. In manual mode, every few accepted batches, run `auto-dataset publish <manifest>` to export the current suite into ignored `artifacts/`, commit and push git changes to GitHub if any, and publish a fresh intermediate snapshot to Hugging Face.
8. Keep the change only if it improves source-grounded coverage, answer-key quality, or rubric clarity.

If you are running through `auto-dataset run`, stop after step 5 and leave the repository ready for validation; the runner appends log rows and handles publish cadence itself.

Treat `auto-dataset summary` as the machine-readable steering surface:

- target gaps show which suite, source-family, and language targets are still below their configured lower bounds
- lifecycle readiness shows whether the current suite mix is mostly under-construction or evaluation-ready
- run-log rollups show whether the loop is still adding net-new cases or spending more effort on zero-growth hardening/maintenance work

## Keep criteria

Keep a change when it does at least one of these:

- adds a new source family with clear answer-key strategy
- turns a vague test idea into a replayable case
- improves provenance completeness
- reduces ambiguity between `exact`, `rubric`, and `mixed` scoring
- adds a defensible journalist-style `gold_candidate` or manually reviewed `gold` annotation

## Discard criteria

Discard a change when it:

- adds cases without sources
- turns public-source cases into synthetic-only exercises
- mixes allegation language into answer keys
- weakens citation grounding
- adds broad framework code without improving case production

## Design principle

The goal is not benchmark theater. The goal is a public validation suite that helps assess whether an investigative assistant remains useful, grounded, and restrained.
