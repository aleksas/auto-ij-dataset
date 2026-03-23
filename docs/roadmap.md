# Roadmap

## Phase 1: Bootstrap suite

Status: complete.

- validate manifest and case structure
- encode the unattended run budget and operating contract in the manifest
- add template cases for the four validation families
- define rubrics for follow-up quality and citation grounding
- record run metadata in `results/runs.tsv` with enough detail to replay or discard a batch

## Phase 2: First real public suite

Status: in progress. The repo now includes the first real official-procurement slice alongside the four cross-family templates.

Status note: the suite manifest now tracks this operational state as `phase_2_in_progress`. Use [`public-validation-v1-status.md`](public-validation-v1-status.md) or `auto-dataset summary datasets/public-validation-v1/manifest.yaml` for live counts; this roadmap is phase narrative, not telemetry.

- replace template placeholders with real public cases
- preserve source files or source URLs for each case
- derive answer keys from official fields where possible
- add one Lithuania-specific official-data slice
- complete one bounded week-long harvesting run without widening the fixed harness

## Phase 3: Integration

- export cases into retrieval and evaluation stacks for benchmark runs
- export rubric-ready prompts for agent evaluation
- add result artifacts comparable across models and workflow versions

## Phase 4: Release path

- publish the public suite under an open license
- harden the autonomous loop and publishing workflow
- document how other investigative projects can contribute cases without breaking provenance requirements
- evaluate whether the first stable public release should be accompanied by an academic dataset paper

See also [`ideas.md`](ideas.md) for follow-on directions that are not yet part of the core roadmap.
