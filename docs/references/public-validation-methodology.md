# Public Validation Methodology

This note summarizes the validation methodology that `auto-dataset` uses.

## Purpose

The project needs more than raw data dumps. It needs:

- task definitions
- answer keys
- rubric-scored cases
- preserved source provenance

For investigative workflows, some tasks can be scored exactly and some cannot.

- field extraction from structured records can often use official fields as answer keys
- entity-link recovery can use published relationships as partial ground truth
- citation grounding can be checked against source passages, page references, or attached metadata
- follow-up suggestion quality usually needs a small manual gold set and a rubric

Without that layer, an investigative system can sound capable without proving where it is useful, where it degrades, and where it overclaims.

## Recommended source mix

Use a mixed public suite rather than a single generic benchmark:

- structured public-record datasets where official fields act as answer keys
- public entity-link datasets with known relationships between companies, officers, addresses, or intermediaries
- public document collections with source files plus attached metadata
- a small manually annotated gold set for journalist-style tasks that do not have one exact machine-readable answer

## Candidate public source families

Useful source families include:

- procurement notices and related structured fields from official procurement portals such as TED
- public investigative document collections such as DocumentCloud public documents
- public entity-link datasets such as Offshore Leaks
- regional or country-specific official open-data slices for local workflow validation

The goal is not benchmark trivia. The goal is to test the workflow layers that an investigative assistant actually claims to support.

## Ground-truth construction

### 1. Structured-record answer keys

Use official structured fields as answer keys where possible.

Typical fields:

- buyer
- supplier
- award date
- amount
- category or code

This supports extraction, normalization, and retrieval checks.

### 2. Known relationship answer keys

Use published entity relationships from public link datasets as partial ground truth.

This supports:

- entity linking
- graph navigation
- cross-reference recovery
- weak-clue expansion

### 3. Metadata-backed document answer keys

Use the source document together with attached metadata.

This supports:

- document conversion checks
- named-entity extraction
- citation grounding
- claim-to-record traceability

### 4. Manual gold annotations

Some journalist-style tasks need a small human gold set because they do not have one exact machine-readable answer.

Typical examples:

- whether a follow-up suggestion is operationally useful
- whether a suggested lead is supported by the source
- whether a citation points to the correct passage or page
- whether the system overreaches beyond what the record supports

This gold set should stay small but high quality.

## Recommended task families

- field extraction from documents and records
- entity resolution and linking
- citation grounding to source passages or pages
- next-step suggestion quality
- degradation testing when moving from stronger online models to weaker local or self-hosted models

## Evaluation principles

- prefer public datasets first, before sensitive-corpus testing
- keep every case tied to a preserved source URL or local source file
- separate exact-answer tasks from rubric-scored tasks
- treat unsupported or overclaimed outputs as failures even when they sound plausible
- measure degradation explicitly when moving from stronger online models to local or self-hosted models

## Practical first version

A defensible first suite can stay compact:

- `50-100` public documents for conversion, extraction, and citation grounding
- `100-300` entity-link cases for resolution and graph-navigation tests
- `100-300` structured public records for field extraction and retrieval validation
- `20-40` manually annotated journalist-style cases for follow-up suggestion quality and evidentiary discipline

## Why this matters for auto-dataset

This is the core design contract for the project:

- cases should be built around public source families first
- answer-key mode must be explicit per case
- provenance is mandatory, not optional
- the project should generate eval-ready datasets rather than only harvest raw files
