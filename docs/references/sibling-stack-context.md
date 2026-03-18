# Sibling Stack Context

This note copies the parts of the sibling investigative stack that matter for `auto-dataset`.

## What the sibling stack already does

The sibling repo described in the surrounding notes is the retrieval and indexing substrate. In this workspace the likely match is `../../investigative-journalism-ai-stack`.

Its documented capabilities include:

- joined Lithuanian company and public-funding dossiers
- high-volume ingestion
- hybrid exact and semantic retrieval
- local-first handling of sensitive investigative work
- retrieval validation for precise lookups and dossier queries

The key point is that it already behaves like a retrieval system, not a dataset-construction framework.

## What auto-dataset should take from that

`auto-dataset` should produce assets that can feed or evaluate that stack:

- retrieval-validation cases
- answer-key manifests
- source-grounded documents and metadata packets
- manual gold cases for citation grounding and follow-up usefulness

## What auto-dataset should not duplicate

It should not try to become:

- the primary ingestion pipeline
- the main search stack
- the document store
- the hybrid retrieval engine

Those already belong in the sibling infrastructure.

## Interface assumption

The clean interface between the projects is:

- sibling stack: ingest, index, retrieve, answer
- `auto-dataset`: define cases, preserve provenance, specify answer keys, score outputs

That division keeps evaluation logic separate from production retrieval logic.

## Retrieval-validation implications

The sibling notes emphasize:

- exact registration-code lookups
- semantic funding-pattern queries
- ingestion and indexing status
- multiple data planes and connector/query paths

That means `auto-dataset` should include cases that distinguish:

- exact retrieval checks
- semantic retrieval checks
- citation grounding checks
- structured extraction checks

## Why this matters for auto-dataset

The project is strongest when it is a bridge layer:

- not only raw data harvesting
- not only benchmark prompts
- not only retrieval infrastructure

Instead it should turn public investigative sources into reusable evaluation artifacts.

## Source references

- `../../investigative-journalism-ai-stack/README.md`
- `../../investigative-journalism-ai-stack/STATUS_UPDATE.md`
- `../../investigative-journalism-ai-stack/docs/INGESTION_QUERY_SCENARIOS.md`
- `../../local-agent/grants/notes/submission-decision-brief-2026-03-17.md`
