# Ideas

## Dataset Paper

After the dataset reaches a stable public release, the project could support an academic paper describing:

- the dataset construction methodology
- source families and provenance rules
- answer-key and rubric design
- autonomous dataset-building workflow
- evaluation tasks, limitations, and failure modes

That paper could help with:

- explaining why the dataset is useful for investigative-journalism systems
- making the methodology easier for others to reproduce
- giving the dataset a citable reference for future research
- documenting design tradeoffs and known limitations

The paper should follow the dataset, not lead it. The priority remains building a strong, source-grounded public suite first.

## Cross-Country Leak Coverage Harvest

Build a case-harvesting track around major leak-related reporting from reputable outlets in different countries.

The point is not just to collect famous leak summaries. The point is to capture how the same leak or adjacent leak aspect was reported, localized, and followed up differently across jurisdictions.

This could support:

- cross-country source comparison cases
- follow-up quality and prioritization cases
- claim-grounding cases built from outlet reporting plus underlying documents
- outcome-tracking cases that distinguish successful, unsuccessful, and unclear downstream results
- literature-backed analysis when academics later studied the same case, network, or reporting wave

Preferred collection pattern:

- identify reputable outlets in multiple countries that published substantive leak reporting or country-specific follow-ups
- identify concrete cases, entities, transactions, procurement episodes, shell-company structures, or enforcement outcomes discussed in those pieces
- collect both outlet articles and academic publications about the same case when they exist
- preserve local reference copies for review, including markdownified article text where practical
- mark every preserved reference with the original source URL and a collection timestamp

For each candidate case, try to capture:

- country or countries involved
- outlet name, article title, publication date, source URL, and collection timestamp
- leak family or source context
- the specific local angle that made the case relevant in that jurisdiction
- whether the reporting describes a successful result, unsuccessful result, attempted but inconclusive result, or no clear downstream result
- any official records, sanctions, prosecutions, procurement documents, company records, or court materials linked from the reporting
- any academic paper, report, or case-study analysis tied to the same facts

If this idea turns into an operational collection workflow, save the raw references in ignored local storage and keep enough metadata to reconstruct provenance later. The immediate dataset value is likely in grounded case briefs, multi-source comparison tasks, and outcome-labeling tasks built from these reporting trails.
