# public-validation-v1 Status Dashboard

> Source of truth for live suite state: regenerate this file with
> `PYTHONPATH=src python3 -m auto_dataset.cli dashboard datasets/public-validation-v1/manifest.yaml --output docs/public-validation-v1-status.md`

> Warning: prose counts in narrative docs can drift. Use this dashboard or
> `auto-dataset summary datasets/public-validation-v1/manifest.yaml` for live counts.

## Suite State

- suite status: `phase_2_in_progress`
- roadmap phase: `Phase 2: First real public suite`
- default loop mode: `acquisition`
- loop mode goal: Grow case count and family breadth fast enough to reach hundreds-scale coverage.
- objective: Build a first public validation suite for investigative-journalism workflow automation using source-grounded cases, explicit answer-key modes, and small manual gold annotations.
- cases total: `65`

## Current Coverage

- by status: template=5, validated=60
- by task type: citation_grounding=1, coverage_comparison=1, entity_linking=4, field_extraction=58, next_step_suggestion=1
- by answer mode: exact=62, mixed=1, rubric=2
- by source family: cross_country_leak_reporting=1, journalist_style_case=1, official_procurement=58, public_documents_with_metadata=1, public_entity_link_dataset=4
- by source tier: manual_annotation=1, primary=63, secondary=1
- by pipeline stage: hardened=60, template=5

## Source Family Balance

- overrepresented families: official_procurement=58
- underrepresented families: cross_country_leak_reporting=1, journalist_style_case=1, public_documents_with_metadata=1, public_entity_link_dataset=4

## Language Coverage

- by case source language: bg=1, cs=1, de=2, el=2, en=37, es=2, fr=7, hr=2, it=2, lv=1, pl=3, pt=2, ro=1, sk=1, sl=1, sv=1
- by source record language: bg=3, cs=3, de=6, el=6, en=82, es=6, fr=19, hr=6, it=6, lv=3, pl=9, pt=6, ro=3, sk=3, sl=3, sv=3
- by evidence language: bg=1, cs=1, de=2, el=2, en=37, es=2, fr=7, hr=2, it=2, lv=1, pl=3, pt=2, ro=1, sk=1, sl=1, sv=1
- by answer language: en=65
- multilingual cases total: `1`

## Target Progress

| target | target range | current | gap to lower bound | basis |
| --- | --- | ---: | ---: | --- |
| documents | 50-100 | 1 | 49 | proxy: source_family=public_documents_with_metadata |
| entity_link_cases | 100-300 | 4 | 96 | proxy: task_type=entity_linking |
| structured_records | 100-300 | 58 | 42 | proxy: task_type=field_extraction |
| manual_gold_cases | 20-40 | 0 | 20 | proxy: status=gold |

## Source Family Target Progress

| source family | target range | current | current share | gap to lower bound | max share |
| --- | --- | ---: | ---: | ---: | ---: |
| cross_country_leak_reporting | 10-40 | 1 | 2% | 9 | n/a |
| journalist_style_case | 10-30 | 1 | 2% | 9 | n/a |
| official_procurement | 60-180 | 58 | 89% | 2 | 85% |
| public_documents_with_metadata | 10-40 | 1 | 2% | 9 | n/a |
| public_entity_link_dataset | 20-80 | 4 | 6% | 16 | n/a |

## Language Target Progress

| language target | target range | current | gap to lower bound | basis |
| --- | --- | ---: | ---: | --- |
| en | 30-150 | 37 | 0 | proxy: case source_languages |
| fr | 5-30 | 7 | 0 | proxy: case source_languages |
| es | 5-30 | 2 | 3 | proxy: case source_languages |
| it | 5-30 | 2 | 3 | proxy: case source_languages |
| pt | 5-20 | 2 | 3 | proxy: case source_languages |
| de | 5-20 | 2 | 3 | proxy: case source_languages |
| pl | 5-20 | 3 | 2 | proxy: case source_languages |
| lt | 5-20 | 0 | 5 | proxy: case source_languages |
| ru | 5-20 | 0 | 5 | proxy: case source_languages |
| multilingual_cases | 10-30 | 1 | 9 | proxy: cases with 2+ source_languages |

## Lifecycle Readiness

- publish includes statuses: `template, harvested, draft, validated, gold_candidate, gold`
- evaluation-ready statuses: `validated, gold`
- default downstream-consumption statuses: `validated, gold`
- included cases total: `65`
- evaluation-ready cases total: `60`
- benchmark-queue cases total: `0`
- benchmark-ready cases total: `0`
- under-construction cases total: `5`
- policy note: Include the full working suite in HF snapshots for transparency and provenance, but default downstream evaluation to validated and gold cases because earlier lifecycle states, including gold_candidate review queues, are still under construction.

| status | count | pipeline stage | published | evaluation-ready | default downstream use |
| --- | ---: | --- | --- | --- | --- |
| template | 5 | template | yes | no | no |
| harvested | 0 | acquisition | yes | no | no |
| draft | 0 | acquisition | yes | no | no |
| validated | 60 | hardened | yes | yes | yes |
| gold_candidate | 0 | benchmark_queue | yes | no | no |
| gold | 0 | benchmark | yes | yes | yes |

## Gap Analysis

- missing suite-level targets: documents, entity_link_cases, structured_records, manual_gold_cases
- underrepresented source families: cross_country_leak_reporting, journalist_style_case, public_documents_with_metadata, public_entity_link_dataset
- overrepresented source families: official_procurement
- underrepresented languages: es, it, pt, de, pl, lt, ru, multilingual_cases
- benchmark-queue cases total: `0`
- benchmark-ready cases total: `0`

| next focus | label | reason |
| --- | --- | --- |
| target_count | documents | suite-level target is still below its configured lower bound |
| target_count | entity_link_cases | suite-level target is still below its configured lower bound |
| target_count | structured_records | suite-level target is still below its configured lower bound |
| target_count | manual_gold_cases | suite-level target is still below its configured lower bound |
| source_family | cross_country_leak_reporting | source family is explicitly underrepresented relative to its target range |
| source_family | journalist_style_case | source family is explicitly underrepresented relative to its target range |
| source_family | public_documents_with_metadata | source family is explicitly underrepresented relative to its target range |
| source_family | public_entity_link_dataset | source family is explicitly underrepresented relative to its target range |
| language | es | language coverage is below its configured lower bound |
| language | it | language coverage is below its configured lower bound |
| language | pt | language coverage is below its configured lower bound |
| language | de | language coverage is below its configured lower bound |
| language | pl | language coverage is below its configured lower bound |
| language | lt | language coverage is below its configured lower bound |
| language | ru | language coverage is below its configured lower bound |
| language | multilingual_cases | language coverage is below its configured lower bound |
| lifecycle | gold_candidate | no review-ready gold_candidate cases exist yet; prepare candidates and defer final gold promotion until reviewer capacity exists |

## Run Log

- logged runs: `35`
- accepted runs: `27`
- rejected runs: `8`
- non-ok runs: `8`
- acceptance rate: `77%`
- failure rate: `23%`
- change kinds: case_batch=4, worker_batch=31
- failure statuses: disallowed_changes=1, no_changes=1, worker_failed=4, worker_timeout=2
- failure classes: environment=4, no_effect=1, policy=1, timeout=2
- accepted by source family: autonomous_loop=23, official_procurement=4
- rejected by source family: autonomous_loop=8
- effort proxies: baseline_unknown=1, failed=8, net_new=21, zero_growth_kept=5
- net-new runs: `21`
- zero-growth kept runs: `5`
- hardening proxy runs: `5`
- total recorded case growth: `60`
- last recorded cases total: `65`
- recent-window case growth: `18` over `10` runs
- recent-window failure rate: `20%`

## Lifecycle Notes

- `template`: scaffold only; not counted as a live acquisition case.
- `harvested` and `draft`: acquisition-stage cases. They must carry a checked-in source document, but raw upstream snapshots can still be deferred.
- `validated`: provenance-hardened case. It must carry both the checked-in source document and at least one raw upstream snapshot artifact.
- `gold_candidate`: review-ready benchmark candidate. It must satisfy validated provenance requirements and carry candidate-preparation metadata, but it is not benchmark-final yet.
- `gold`: benchmark-stage case. It must satisfy validated provenance requirements and include review metadata.

### Recent Outcomes

| run_id | timestamp | cases_total | validation_status | source_family | kept | description |
| --- | --- | ---: | --- | --- | --- | --- |
| run-016 | 2026-03-20T12:14:34+00:00 | 64 | ok | autonomous_loop | true | accepted autonomous batch; 4 mutable file(s) changed |
| run-017 | 2026-03-20T12:14:53+00:00 | 64 | worker_failed | autonomous_loop | false | WARNING: proceeding, even though we could not update PATH: Refusing to create helper binaries under temporary dir "/tmp" (codex_home: "/tmp/codex-home/.codex... |
| run-001 | 2026-03-20T12:16:12+00:00 | 64 | worker_failed | autonomous_loop | false | WARNING: proceeding, even though we could not update PATH: Refusing to create helper binaries under temporary dir "/tmp" (codex_home: "/tmp/codex-home/.codex... |
| run-001 | 2026-03-22T17:25:49+00:00 | 65 | ok | autonomous_loop | true | accepted autonomous batch; 3 mutable file(s) changed |
| run-001 | 2026-03-22T17:36:58+00:00 | 65 | ok | autonomous_loop | true | accepted autonomous batch; 3 mutable file(s) changed |

### Case Growth

| run_id | timestamp | cases_total | case_delta | source_family | change_kind |
| --- | --- | ---: | ---: | --- | --- |
| run-008 | 2026-03-20T11:07:44+00:00 | 41 | 3 | autonomous_loop | worker_batch |
| run-009 | 2026-03-20T11:19:10+00:00 | 44 | 3 | autonomous_loop | worker_batch |
| run-010 | 2026-03-20T11:29:09+00:00 | 47 | 3 | autonomous_loop | worker_batch |
| run-011 | 2026-03-20T11:36:10+00:00 | 50 | 3 | autonomous_loop | worker_batch |
| run-012 | 2026-03-20T11:43:48+00:00 | 53 | 3 | autonomous_loop | worker_batch |
| run-013 | 2026-03-20T11:53:18+00:00 | 56 | 3 | autonomous_loop | worker_batch |
| run-014 | 2026-03-20T11:59:18+00:00 | 58 | 2 | autonomous_loop | worker_batch |
| run-015 | 2026-03-20T12:07:40+00:00 | 61 | 3 | autonomous_loop | worker_batch |
| run-016 | 2026-03-20T12:14:34+00:00 | 64 | 3 | autonomous_loop | worker_batch |
| run-001 | 2026-03-22T17:25:49+00:00 | 65 | 1 | autonomous_loop | worker_batch |

## Status Surface Rules

- `auto-dataset summary` is the machine-readable live count source.
- This dashboard is the human-readable live status source.
- `datasets/public-validation-v1/manifest.yaml` is the source of truth for operating contract and targets.
- `docs/roadmap.md` is the source of truth for phase narrative, not live telemetry.
- Case-level language coverage is measured from `source_languages`; source-level language coverage is measured from `sources[].language`.
