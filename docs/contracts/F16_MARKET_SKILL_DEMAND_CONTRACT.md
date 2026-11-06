# F16 Market Skill Demand Analysis Contract

Status: Proposed low-priority contract for team review.
Prepared by: Sampreet Ajjanagouda Patil (@Sampreet26).
Implementation ownership: To be assigned after the integration checkpoint.

F16 analyzes a collection of job descriptions for a selected target role. It reports recurring skills and compares those skills with the job seeker's approved career evidence.

Results describe the analyzed collection. They must not be presented as a complete or representative measure of the employment market unless the dataset supports that claim.

This document defines intended behavior. It does not establish that the implementation is complete.

## Scope

F16 supports the following SRS requirements:

- Req-Func-Sw-87: Analyze a collection of job descriptions for a selected target role.
- Req-Func-Sw-88: Report skill frequency across the analyzed descriptions.
- Req-Func-Sw-89: Compare recurring skills with approved career evidence.
- Req-Func-Sw-90: Report supported skill strengths and recurring skill gaps.

Automated job-board scraping, employment forecasts, salary estimates, and hiring-probability predictions are outside this proposed contract.

## Dependencies and boundaries

F16 uses F04's public normalized requirement contract rather than importing parser implementation classes.

Skill normalization uses the documented taxonomy interface. F16 does not directly modify taxonomy storage.

Personalized comparisons obtain approved evidence through F02's public service contract. Where requirement matching is needed, F16 consumes the F05 contract rather than duplicating its implementation.

F16 does not change evidence approval, generate resume claims, or grant export eligibility.

## Identity and collection access

Personalized analysis uses the authenticated Job Seeker identity supplied by F01.

The system checks access to every submitted or stored job-description reference. A caller cannot analyze another user's private collection by changing an ID.

Approved evidence is resolved for the authenticated user. Private evidence text must not appear in another user's aggregate results.

## Input

The proposed input includes:

- The selected target role.
- A collection of job descriptions or authorized references to them.
- Available source identifiers and collection dates.
- The taxonomy version used for normalization.
- The recurrence threshold used to identify recurring skills.

Each description must have a stable identifier within the collection. The target role and collection must be nonempty.

The recurrence threshold is a positive minimum posting count. Its value is included in the output rather than left implicit.

The collection's relevance to the target role must be established by its documented selection process. F16 does not silently assume that unrelated postings describe the same role.

## Extraction and normalization

F04 identifies skill requirements and preserves their supporting source text.

F16 maps equivalent terms to canonical skill identifiers using documented taxonomy rules. Original terms and source references remain available for explanation.

Ambiguous terms are retained for review rather than silently merged. For example, Java and JavaScript must not be treated as the same skill.

Taxonomy changes require a new analysis or an explicit indication that the result uses an older taxonomy version.

## Duplicate and invalid descriptions

The proposed baseline excludes repeated source identifiers and exact duplicate descriptions after normalizing line endings and surrounding whitespace.

This does not establish that differently worded postings are independent vacancies. Any additional deduplication method must be documented.

Invalid or unparseable descriptions are identified with reasons and excluded from the frequency denominator. The result reports submitted, duplicate, excluded, and successfully analyzed counts.

If no valid unique descriptions remain, the operation returns a clear validation error. It does not generate percentages from an empty collection.

## Skill frequency

A skill is counted at most once per successfully analyzed unique description, even when it appears several times in that description.

posting_count is the number of analyzed descriptions containing the skill.

posting_percentage is calculated as:

100 × posting_count / analyzed_description_count

Every frequency result includes its denominator. A percentage is not a measure of the user's competence or probability of receiving an offer.

A skill is recurring when its posting_count meets the reported recurrence threshold.

Explicitly required, preferred, optional, and unspecified mentions retain their distinctions. An ambiguous or conflicting priority must not be relabeled as required.

If a skill has several priority classifications within one posting, the result preserves that information and explains that category counts may overlap.

## Comparison with career evidence

F16 compares recurring skill requirements with current approved evidence obtained through F02.

The comparison preserves F05's Strongly Supported, Partially Supported, and Unsupported classifications and their explanations.

Skill mentions with different conditions are not collapsed into a claim that the user satisfies every posting. For example, approved evidence of a Docker tutorial does not establish production Docker experience.

When support differs across requirements for the same skill, the result reports the distribution and limitations rather than assigning an unexplained overall classification.

An Unsupported result means that available approved evidence does not support the requirement. It does not prove that the user lacks the skill.

## Output

The proposed analysis result includes:

- The target role and analysis identifier.
- The taxonomy version and recurrence threshold.
- Collection dates where available.
- Submitted, duplicate, excluded, and analyzed description counts.
- Canonical skill identifiers and original terms.
- Per-skill posting counts and percentages.
- Source description and requirement references.
- Priority information and extraction warnings.
- Evidence support classifications and explanations.
- Supported strengths and recurring evidence gaps.

Skills are ordered by descending posting_count, with a stable canonical identifier used to resolve ties.

Supported strengths reference approved evidence. Recurring gaps identify missing or insufficient support and preserve uncertainty about the user's actual qualifications.

## Data limitations

Results must identify the collection size and known source limitations.

A collection without reliable dates cannot support claims about recent changes in demand. A single collection cannot establish a time trend.

Small or narrowly selected collections must be described as such. The report must not imply statistical representativeness, complete market coverage, or guaranteed employment outcomes.

## Failure behavior

Malformed input, unauthorized collection references, and unsupported contract versions produce clear errors.

Individual invalid descriptions may be excluded with explicit reasons. A systemic extraction-service failure must be reported as a failure rather than silently treated as invalid input.

If F02 or F05 is unavailable, personalized comparison is unavailable. The system must not classify every skill as Unsupported merely because evidence retrieval or matching failed.

An aggregate-only result may be returned if clearly labeled as lacking personalized comparison.

Previously stored personalized results must be refreshed when supporting evidence changes. Changes to evidence do not alter the original collection's skill-frequency counts.

## Acceptance checks

The implementation must demonstrate that:

- Each skill is counted once per analyzed unique description.
- Duplicate and invalid descriptions are excluded transparently.
- Counts, denominators, and percentages agree.
- Taxonomy normalization preserves distinct and ambiguous skills.
- Source references explain each reported skill occurrence.
- Personalized comparisons use only the user's current approved evidence.
- Service failures are distinguished from unsupported qualifications.
- Recurring gaps and supported strengths include explanations.
- Repeated analysis with identical inputs and configuration is deterministic.
- Reports state collection limitations without claiming market-wide certainty.