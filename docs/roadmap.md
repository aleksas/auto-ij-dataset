# Roadmap

## Phase 1: Bootstrap suite

- validate manifest and case structure
- encode the unattended run budget and operating contract in the manifest
- add template cases for the four validation families
- define rubrics for follow-up quality and citation grounding
- record run metadata in `results/runs.tsv` with enough detail to replay or discard a batch

## Phase 2: First real public suite

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
