# System Boundaries

`auto-dataset` should produce evaluation artifacts that other systems can consume without taking ownership of those systems.

## What this project should do

- define replayable cases
- preserve provenance
- specify answer keys and rubrics
- export stable evaluation artifacts
- record run metadata and publishing state

## What this project should not do

It should not try to become:

- the primary ingestion pipeline
- the main retrieval engine
- the document store
- a generic benchmark framework detached from investigative work
- a newsroom production application

## Clean interface

The clean interface is:

- `auto-dataset`: define cases, preserve provenance, specify answer keys, score outputs, export artifacts
- downstream systems: ingest artifacts, retrieve evidence, generate answers, run comparisons

That division keeps evaluation logic separate from production retrieval or application logic.

## Integration implications

Export formats should stay simple and durable.

That means the project should continue to support:

- exact retrieval checks
- semantic retrieval checks
- citation grounding checks
- structured extraction checks
- manual gold-case evaluation

## Why this matters

The project is strongest when it produces reusable evaluation artifacts rather than duplicating adjacent system layers.
