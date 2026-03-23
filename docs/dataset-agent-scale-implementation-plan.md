# Dataset Agent Scale Implementation Plan

This plan turns the current provenance-heavy first slice into a higher-throughput dataset program that can reach hundreds of cases with stronger multilingual coverage.

Use this as a live checklist. Mark a task complete only when all of its substeps are complete and the stated exit criteria are met.

## Success Criteria

- [ ] The suite can grow beyond the current bounded throughput without weakening provenance or validation integrity.
- [ ] The suite has a formal lifecycle that distinguishes fast harvesting from stricter validation and conditional gold curation.
- [ ] Multilingual coverage is explicitly measured and enforced rather than inferred ad hoc.
- [ ] The autonomous loop can prioritize breadth targets across source families instead of overfilling procurement alone.
- [ ] Progress reporting stays aligned with live suite counts, targets, and recent run outcomes.

## Phase 1: Fix Status Visibility And Planning Surfaces

- [x] Align all human-readable status surfaces with the actual suite state.
  - [x] Update `README.md` so the "Current suite status" section reflects live counts and no longer says `17` total cases.
  - [x] Decide whether `datasets/public-validation-v1/manifest.yaml` should remain `bootstrap` or move to a more accurate suite status.
  - [x] Add a short status note to `docs/roadmap.md` that explains the current phase in relation to the manifest status.
  - [x] Document which file is the source of truth for live counts, phase, and target attainment.
  - Exit criteria: the README, roadmap, and manifest no longer give conflicting impressions about the suite's maturity.

- [x] Add a concise progress dashboard artifact for humans.
  - [x] Define the minimum fields to expose, including total cases, by-status counts, by-family counts, by-task counts, and recent run outcomes.
  - [x] Decide whether the dashboard should be generated into `docs/`, `results/`, or printed only by CLI.
  - [x] Add a stable place where current gaps versus target counts are visible at a glance.
  - [x] Include a visible warning when counts in prose docs are stale relative to the suite summary.
  - Exit criteria: a maintainer can inspect one artifact and understand the current suite state without reading multiple files.

## Phase 2: Introduce A Real Case Lifecycle

- [x] Define a status ladder that supports both throughput and quality control.
  - [x] Propose allowed statuses such as `harvested`, `draft`, `validated`, and `gold`.
  - [x] Define the meaning of each status in operational terms rather than aspirational terms.
  - [x] Decide which statuses are allowed for templates and which are allowed for real cases.
  - [x] Define who or what can promote a case between statuses.
  - Exit criteria: each status has a precise contract that can be validated and understood by both humans and agents.

- [x] Add validation rules for the new lifecycle.
  - [x] Specify the minimum required fields for `harvested` cases.
  - [x] Specify the additional requirements for `draft` and `validated` cases.
  - [x] Specify the stricter requirements for `gold` cases, including review provenance and scoring discipline.
  - [x] Decide which requirements are warnings versus hard validation failures at each status.
  - Exit criteria: the validator can distinguish incomplete fast-harvest cases from benchmark-ready cases without ambiguity.

- [x] Migrate current cases into the new lifecycle.
  - [x] Define a mapping from today's `template` and `draft` statuses into the new ladder.
  - [x] Identify which current cases already satisfy `validated` semantics.
  - [x] Confirm that no current case is mislabeled as `gold`.
  - [x] Backfill status values across all checked-in case YAML files.
  - Exit criteria: every case uses the new status vocabulary and the mapping is documented.

## Phase 3: Split Harvesting From Provenance Hardening

- [x] Introduce a fast acquisition stage for net-new cases.
  - [x] Define the minimum viable record for a newly harvested case, including source URL, high-level source family, task type, and provisional evidence content.
  - [x] Decide whether raw upstream snapshots are mandatory at harvest time or can be deferred to a later stage.
  - [x] Decide whether `content_markdown` can be provisional for the first stage.
  - [x] Specify what makes a harvested case keepable versus discardable.
  - Exit criteria: the agent can add cases quickly without immediately paying full finalization cost.

- [x] Introduce a provenance-hardening stage.
  - [x] Define the requirements for adding local source documents, raw source snapshots, digests, and artifact metadata.
  - [x] Specify how a case graduates from fast-harvested to provenance-complete.
  - [x] Define retry behavior for sources that are temporarily unavailable or partially recoverable.
  - [x] Decide how to handle sources that cannot legally or practically be snapshotted.
  - Exit criteria: provenance-hardening is a distinct, replayable workflow rather than an implicit side effect of case creation.

- [x] Introduce a gold-curation stage.
  - [x] Define which case families are eligible for gold curation.
  - [x] Specify the review workflow for `gold_candidate` preparation, gold labels, and rubrics.
  - [x] Define reviewer metadata, candidate-preparation metadata, and signoff requirements.
  - [x] Decide whether gold promotion requires dual review for high-risk journalist-style tasks.
  - Exit criteria: gold cases have an explicit manual curation path rather than being informal drafts.

## Phase 4: Raise Throughput In The Autonomous Loop

- [x] Rework the autonomous run budget for a hundreds-scale target.
  - [x] Decide whether the `7`-day timebox remains appropriate.
  - [x] Reassess `runs_per_day`, `max_total_runs`, `max_case_edits_per_run`, and `max_new_cases_per_run`.
  - [x] Model the theoretical maximum throughput under the new budget.
  - [x] Model the expected net-new throughput after validation failures and backfill overhead.
  - Exit criteria: the run budget is consistent with the stated ambition of reaching hundreds of cases.

- [x] Add separate loop modes for acquisition and hardening.
  - [x] Define one mode that optimizes for finding and drafting new cases.
  - [x] Define one mode that optimizes for artifact recovery, metadata completion, and digest verification.
  - [x] Define one mode for gold-case review and adjudication.
  - [x] Document which mutable paths and frozen paths apply to each mode.
  - Exit criteria: agents are no longer forced to use one loop shape for fundamentally different types of work.

- [x] Improve failure handling and rerun behavior.
  - [x] Classify failure types such as environment failure, usage limit failure, source fetch failure, schema failure, and validation failure.
  - [x] Define what the runner should retry automatically versus what should be surfaced for manual intervention.
  - [x] Add a way to distinguish failed runs that produced no useful output from partial runs that should be resumed.
  - [x] Make recent failure patterns visible in the run log summary.
  - Exit criteria: loop failures stop quietly eroding throughput and become measurable operational events.

## Phase 5: Make Multilingual Coverage A First-Class Constraint

- [x] Add explicit language metadata to cases and sources.
  - [x] Define required per-case language fields.
  - [x] Define required per-source language fields.
  - [x] Decide how to represent multilingual source bundles for one case.
  - [x] Document the difference between source language, evidence language, and answer language.
  - Exit criteria: multilingual coverage can be measured from structured data rather than inferred from filenames.

- [x] Add multilingual target tracking.
  - [x] Define target counts by language or language group for the suite.
  - [x] Define minimum multilingual mix requirements for relevant source families.
  - [x] Decide how multilingual targets interact with source-family targets.
  - [x] Add a report that highlights underrepresented languages and overrepresented families.
  - Exit criteria: maintainers can see where multilingual coverage is thin before the suite drifts further.

- [x] Add explicit multilingual harvesting rules for leak-reporting clusters.
  - [x] Require at least two languages for any accepted `cross_country_leak_reporting` batch.
  - [x] Define acceptable outlet and source-quality standards by language.
  - [x] Define when academic or official follow-on material is needed to stabilize a cluster.
  - [x] Decide how to score contradiction, novelty, and overlap across language variants.
  - Exit criteria: the multilingual reporting family has a real operating discipline rather than a manifest aspiration.

## Phase 6: Rebalance Coverage Across Source Families

- [x] Add quotas or guardrails to prevent procurement overconcentration.
  - [x] Decide whether to use hard caps, soft warnings, or weighted priorities.
  - [x] Define an acceptable ratio between procurement, entity-link, citation-grounding, leak-reporting, and manual-gold slices.
  - [x] Add summary warnings when one family dominates new additions for too long.
  - [x] Define when a batch should be rejected because it worsens family imbalance.
  - Exit criteria: the suite no longer grows almost exclusively in the easiest source family.

- [x] Strengthen the weaker families with dedicated acquisition strategies.
  - [x] Define a repeatable acquisition method for `public_entity_link_dataset` cases.
  - [x] Define a repeatable acquisition method for `public_documents_with_metadata` cases.
  - [x] Define a repeatable acquisition method for `manual_gold_annotations`.
  - [x] Define dedicated search and preservation rules per family rather than relying on one generic loop.
  - Exit criteria: weaker families have their own pipeline logic and are no longer starved by the default procurement-first flow.

## Phase 7: Improve Tooling And Reporting

- [x] Expand the suite summary into a gap-analysis tool.
  - [x] Add target-versus-actual reporting by source family.
  - [x] Add target-versus-actual reporting by language.
  - [x] Add by-status reporting under the new lifecycle.
  - [x] Add recent throughput and failure-rate reporting from `results/runs.tsv`.
  - Exit criteria: one summary command can explain both current coverage and what is missing next.

- [x] Add lifecycle-aware validation and publishing outputs.
  - [x] Ensure publish outputs identify which cases are harvested, validated, or gold.
  - [x] Ensure validators explain lifecycle failures clearly enough for agents to repair them.
  - [x] Decide whether HF snapshots should include non-final cases or only selected statuses.
  - [x] Document how lifecycle state affects downstream evaluation use.
  - Exit criteria: downstream consumers can tell which cases are benchmark-ready and which are still under construction.

- [x] Improve run-log usefulness for dataset steering.
  - [x] Add rollups for accepted versus rejected runs by source family.
  - [x] Add rollups for net-new cases versus pure backfill runs.
  - [x] Add a compact view of case-count growth over time.
  - [x] Add a way to spot when the loop is spending too much effort on provenance hardening relative to acquisition.
  - Exit criteria: the run log becomes a steering tool instead of just a historical ledger.

## Phase 8: Conditional Gold-Case Creation

Only execute this phase when reviewer capacity is actually available. Until then, prepare `gold_candidate` cases and stop short of `gold`.

- [ ] Build a `gold_candidate` review queue first.
  - [ ] Define a minimum first tranche of review-ready `gold_candidate` cases.
  - [ ] Select candidate source materials from existing validated cases where possible.
  - [ ] Write review rubrics that are specific enough for consistent scoring.
  - [ ] Record candidate-preparation metadata and adjudication notes for later reviewers.
  - Exit criteria: the suite contains a durable `gold_candidate` queue even if no immediate manual signoff capacity exists.

- [ ] Convert the current gold template into real gold cases when reviewers are available.
  - [ ] Confirm that reviewer capacity is committed for the tranche.
  - [ ] Promote only reviewed `gold_candidate` cases to `gold`.
  - [ ] Record reviewer identity, date, and adjudication notes.
  - [ ] Decide whether any high-risk journalist-style cases require dual review before promotion.
  - Exit criteria: the suite contains real gold cases rather than only a template.

- [ ] Add gold-case governance.
  - [ ] Define how gold cases are updated when source material or rubric guidance changes.
  - [ ] Define deprecation rules for gold cases that become stale or ambiguous.
  - [ ] Decide whether gold cases require lockstep versioning with the suite.
  - [ ] Add a lightweight review cadence for the gold slice.
  - Exit criteria: the gold subset is durable and auditable.

## Recommended Execution Order

- [ ] Complete Phase 1 first so status and reporting are trustworthy.
- [ ] Complete Phase 2 before changing harvesting policy so the new volume has somewhere sensible to land.
- [ ] Complete Phase 3 and Phase 4 next so throughput can increase without abandoning provenance discipline.
- [ ] Complete Phase 5 and Phase 6 in parallel once lifecycle and loop changes are underway.
- [ ] Complete Phase 7 before claiming the system is steering itself well.
- [ ] Complete Phase 8 only after enough validated cases exist and reviewer capacity is committed.

## Immediate Next Actions

- [ ] Decide the target operating goal for the next iteration.
  - [ ] Choose one of: higher throughput, stronger multilingual breadth, better gold coverage, or better observability.
  - [ ] Set a concrete short-term target such as "reach 120 harvested cases" or "reach 10 multilingual leak clusters."
  - Exit criteria: the next round of implementation work has a measurable objective.

- [ ] Start with the minimum enabling changes.
  - [ ] Update the status vocabulary proposal.
  - [ ] Rewrite the autonomous loop budget proposal.
  - [ ] Add explicit language metadata requirements.
  - [ ] Update summary/reporting requirements.
  - Exit criteria: the repo has enough scaffolding to begin implementation without re-litigating the plan.
