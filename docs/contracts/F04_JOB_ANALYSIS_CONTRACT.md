# F04 Job Description Analysis Contract

Owner: Sampreet Ajjanagouda Patil (@Sampreet26).
Status: Existing deterministic parser prototype; production authentication integration remains pending.

F04 transforms a supplied plain-text job description into normalized requirements for F05/F06. This document describes the existing public contract.

## Public interfaces

Python consumers import the DTOs from:

```python
from app.modules.job_analysis.contracts import AnalysisRequest, AnalysisResult
```

The producer entry point is
`service.analyze_job_description(AnalysisRequest(...))`.

The standalone demo exposes POST `/api/f04/analyze` and returns the same
AnalysisResult contract.

Consumers must not import parser.py, regular expressions, or internal parsing helpers.

## Input

AnalysisRequest contains job_description, a strict string containing between
1 and 50,000 characters.

The input must contain meaningful plain text. Empty or whitespace-only input, unsupported control characters, HTML/markup, and JSON-document text are rejected.

The original whitespace is preserved because source offsets refer to the submitted text.

## Analysis result

AnalysisResult contains:

- schema_version: Currently "1.0".
- document_id: SHA-256 of the original input text.
- requirements: A nonempty list of normalized requirement records.
- warnings: Analysis-level warnings.

The document ID identifies a particular text revision. Requirement IDs are deterministic within that revision but may change when preceding input changes.

Consumers use the pair (document_id, requirement.id) as the requirement reference.

## Requirement fields

Each requirement includes:

- id: The requirement identifier.
- text: The extracted requirement text.
- categories: One or more of skill, education, experience, responsibility, or qualification.
- importance: Critical, Preferred, Optional, or null.
- importance_basis: explicit, section, unspecified, or conflicting.
- source: Original source text and location information.
- experience: Structured experience expectations when extractable, otherwise null.
- needs_review: Whether the requirement needs review.
- review_reasons: Explanations of identified ambiguity.

Multiple categories classify a clause. They do not turn it into separate mandatory conditions.

## Importance and ambiguity

Explicit importance wording overrides section defaults.

Unstated or conflicting importance remains null rather than being guessed. This prototype decision requires team agreement before production integration of Req-Func-Sw-20.

Alternatives such as "Python or Java" remain together and are flagged for review. Consumers must not interpret them as requiring both skills.

Review flags and reasons must remain visible in downstream processing. Ambiguous requirements must not silently become mandatory conditions.

## Source context

SourceContext contains text, start, end, line, and section.

start and end are zero-based Python Unicode character offsets, with end excluded. line is one-based, and section may be null.

Consumers must slice the original submitted text without trimming or normalizing it first.

JavaScript uses UTF-16 string offsets. Consumers can recover the corresponding source span with:

```javascript
Array.from(original).slice(start, end).join("")
```

The existing review interface displays source.text directly.

## Experience expectations

ExperienceExpectation preserves the original expression and may include
minimum_years, maximum_years, and stated_years.

Numeric durations are normalized to years. Ranges preserve their lower and upper bounds.

An amount without an explicit bound is recorded as stated_years. It must not automatically be treated as an exact mandatory duration.

Multiple experience alternatives retain their wording and review flags rather than being collapsed into a misleading range.

## Errors

Request validation failures and descriptions with no recognizable requirements return HTTP 422 with a nonempty detail.

The service raises UnparseableDescription when it cannot identify requirements. The router converts that exception into the HTTP error response.

Malformed input must not produce a successful analysis containing invented requirements.

## Authentication and persistence

The existing demo runs separately from the main application and requires
APP_ENV=development.

The prototype router is not registered in app.main and does not provide the production authentication integration. It must not be deployed publicly without that integration.

Analysis is not persisted. The local prototype does not require an API key, database, or external AI service.

Production integration must use the team's F01 authentication boundary and receive Technical Manager review.

## Consumer example

```python
from app.modules.job_analysis.contracts import AnalysisResult

analysis = AnalysisResult.model_validate(payload)

for requirement in analysis.requirements:
    if requirement.needs_review:
        continue  # Route this requirement to review.
    # Pass the requirement to matching with approved evidence.
```

F04 describes job requirements; it does not determine whether the user satisfies them. F05 owns evidence matching, and F06 owns content selection.

## Versioning and supporting files

Breaking field or semantic changes require a schema version change and coordinated consumer review.

- [JSON Schema](../F04/analysis-result.schema.json)
- [Example analysis result](../F04/example-result.json)
- [Demo setup and verification instructions](../F04/README.md)
- [Validation record](../F04/VALIDATION.md)
- [Frontend consumer types](../../apps/web/src/features/job-analysis/contract.ts)

The schema and example remain in docs/F04/ so existing references continue working.

## Prototype limitations

The parser uses English section headings, phrase rules, and a limited skill vocabulary. It handles line and bullet entries, semicolon clauses, and recognized company or benefit sections.

It does not provide general language understanding, an exhaustive skill taxonomy, PDF parsing, multilingual support, or reliable interpretation of arbitrary prose.

Review is required before matching. No extraction-accuracy claim is made.

## Requirement coverage

This contract supports Req-Func-Sw-18 through Req-Func-Sw-22: job-description submission, structured extraction, importance classification, source traceability, and requirement review.

Existing tests cover representative postings, source offsets, ambiguity, experience expressions, invalid inputs, deterministic identifiers, serialization, and parser-independent consumer imports.