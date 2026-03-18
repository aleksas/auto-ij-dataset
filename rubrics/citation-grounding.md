# Citation Grounding Rubric

Score each response on a `0-2` scale per dimension.

## Dimensions

- `passage_match`: does the cited passage actually support the claim
- `location_precision`: is the citation precise enough to review quickly
- `claim_restraint`: does the response avoid saying more than the cited text supports
- `source_traceability`: can a reviewer get back to the original record

## Interpretation

- `2`: correct and operationally reviewable
- `1`: partly correct but imprecise or weakly grounded
- `0`: unsupported, mismatched, or unverifiable

Treat confident but unsupported citations as failures.
