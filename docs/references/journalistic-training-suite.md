# Journalistic Training Suite

This note captures the journalistic case-design principles that directly guide `auto-dataset`.

## Core goal

The suite should test whether a system can:

- identify plausible corruption or abuse indicators
- separate suspicion from proof
- preserve citations to the source material
- suggest the next defensible investigative step

The suite should reward disciplined investigative reasoning, not theatrical accusation.

## Scenario families

Useful case families include:

- procurement favoritism hidden behind formally legal bidding
- grants or subsidies routed through linked entities
- conflict-of-interest patterns between officials and private entities
- revolving-door hiring followed by favorable decisions
- permit, zoning, or land-use gains that rely on insider timing
- beneficial-ownership concealment through layered entities
- related-party transfers that look legal on paper but defeat policy intent
- repeated use of shell entities, proxies, or nominee managers
- threshold or reporting-rule gaming to avoid scrutiny

The suite should include a mix of:

- clearly illegal cases
- ethically suspect but not yet illegal cases
- formally legal but likely abusive cases
- suspicious-looking but ultimately explainable cases

That mix matters because false positives are a central failure mode in investigative work.

## Input shape

Each fixture should contain a compact but realistic evidence bundle such as:

- company registry extracts
- procurement records
- grant award tables
- official declarations
- planning or permit notices
- property or transaction breadcrumbs
- short media excerpts or public statements
- timeline notes

The material should be messy enough to require synthesis, but bounded enough that a human evaluator can still judge the result.

## Expected outputs

Each case should test whether the system can produce:

- the main suspicious pattern or patterns
- the strongest supporting datapoints
- the missing evidence needed before stronger claims
- a claim-status split between lead, verified fact, and unresolved allegation
- concrete next checks such as registry lookups, record requests, or conflict checks

## Scoring dimensions

The suite should score more than answer matching.

- signal detection: did it notice the important pattern
- false-positive control: did it avoid overstating weak evidence
- provenance discipline: did it cite the relevant records
- investigative prioritization: did it pick the most useful next step
- legal and editorial restraint: did it distinguish suspicion from proof
- structured output quality: can the result be reused downstream

## Good first version

Start small:

1. Build `5-10` hand-authored cases.
2. Give each case a bounded evidence pack and answer key.
3. Include both obvious and ambiguous cases.
4. Require source citations and next-step suggestions.
5. Score both missed patterns and overclaims.

## Why this matters for auto-dataset

`auto-dataset` should not stop at extraction benchmarks. It should also make room for bounded investigative case packs where:

- the evidence bundle is explicit
- the scoring dimensions are explicit
- restraint is tested, not assumed
- follow-up quality is judged as part of system performance
