# F06 Content Selection Contract

Status: Proposed contract for team review.
Owner: Sampreet Ajjanagouda Patil (@Sampreet26).

F06 ranks and selects approved career evidence relevant to an analyzed job description. It uses F05 matching results and the selected resume template's content limits to prepare an evidence selection for F07.

This document defines intended behavior. It does not establish that the implementation is complete.

## Dependencies and boundaries

F04 supplies normalized job requirements. F05 supplies requirement-to-evidence matches, support classifications, explanations, and review warnings.

F06 obtains current approved evidence through F02's public service contract. It does not query evidence tables or import F04 parser or F05 matching implementation classes.

F06 selects evidence. F07 generates candidate statements, F08 verifies claims, F09 records user approval, and F10 controls document layout and export.

## Identity and approved evidence

The HTTP boundary uses F01 to resolve the authenticated Job Seeker. A request-body user ID must not override that identity.

Evidence is resolved through F02 for that user. Only current, owned, APPROVED records are eligible.

Client-supplied evidence text or approval flags cannot establish eligibility. Unknown, foreign-owned, deleted, and unconfirmed evidence must not be accepted as approved support.

## Input

The proposed selection input includes:

- The F04 document ID and normalized requirements.
- F05 matching results for those requirements.
- The selected resume template identifier and content limits.
- Any user-selected evidence IDs or exclusions.

The authenticated user ID is supplied separately by the trusted application boundary.

Matching results must refer to the same analyzed document. Evidence references and approval state must be checked against F02 before selection.

Template limits come from the documented template contract. Missing limits must produce a clear configuration error rather than an invented default.

## Ranking rules

F06 prioritizes evidence that supports the target job's requirements.

Ranking considers requirement importance, support classification, requirement coverage, and relevance. It preserves the distinction between a Critical requirement and a strongly supported requirement.

A record that supports several relevant requirements may be selected once and retain all applicable requirement references. Repeated keywords must not increase relevance merely because they appear frequently in the same record.

Ties use a documented, stable ordering so identical inputs and configuration produce the same selection.

The ranking policy must be versioned. Numerical weights are implementation decisions that require documentation and tests before they are treated as established behavior.

## Selection rules

F06 selects relevant approved evidence within the supplied template limits.

Unconfirmed evidence is excluded from automatic selection. Unrelated evidence must not be added solely to fill unused capacity.

Partially supported evidence may be selected when relevant, but its limitations and review warnings remain attached. Selection must not imply that an unmet qualification has been satisfied.

F06 must not rewrite evidence, combine employment dates into an unsupported experience duration, or invent qualifications.

Evidence selection alone cannot guarantee that generated text fits the final rendered document. F10 remains responsible for layout validation.

## User adjustments

Any user-adjusted selection is revalidated against ownership, approval, uniqueness, and applicable content limits.

An explicitly selected invalid evidence ID causes the selection to fail in full. F06 must not silently remove it and continue with a different selection.

If the selection exceeds a limit, the system explains the conflict and requires a revised selection. It does not silently discard user choices.

## Output

The proposed selection result includes:

- The analyzed document ID.
- The template identifier and applied limits.
- The ranking policy version.
- An ordered list of unique selected evidence IDs.
- Related requirement IDs and selection explanations.
- Evidence approval timestamps used for the selection.
- Uncovered requirements, exclusions, and review warnings.

Explanations identify why evidence was selected and what it supports. They do not describe selected evidence as a verified or approved generated statement.

## Handoff to F07

The existing F07 GenerationPreviewRequest accepts job_context,
evidence_ids, and max_statements.

F06 supplies the ordered evidence_ids and compatible job context through a documented adapter. The current F07 boundary accepts one to twenty unique evidence IDs. F06 must not submit more than twenty IDs or silently truncate an oversized selection.

max_statements remains within F07's existing range of one to ten. The number of selected evidence records does not automatically determine the number of generated statements.

An empty eligible selection produces a clear no-content result. F06 must not invoke F07 with an empty evidence_ids collection.

F07 independently resolves the selected IDs through F02. F06's earlier validation does not replace F07's approved-evidence checks.

## Evidence changes

Selection reflects the evidence available at the time it was produced.

Before reusing a selection, the integration revalidates the referenced records through F02. Changed or unconfirmed evidence requires refreshed matching and selection.

If evidence becomes invalid before generation, F07's existing rejection behavior applies. The user receives an explanation and can refresh the selection.

## Failure behavior

Malformed inputs, duplicate explicit evidence IDs, mismatched document references, and invalid limits produce clear validation errors.

An F02 retrieval failure is reported as a service failure, not as an empty evidence collection.

Unavailable or stale F05 results prevent selection until matching is available or refreshed.

The operation does not modify evidence records, their approval states, or previously saved resume versions.

## Acceptance checks

The implementation must demonstrate that:

- Only current approved evidence belonging to the user is selected.
- Relevant evidence ranks ahead of unrelated evidence.
- Duplicate references do not produce duplicate selected records.
- Supplied template limits and F07's input limits are enforced.
- Partial support and ambiguity remain visible.
- Invalid explicit selections are rejected without silent trimming.
- Empty selections do not trigger generation.
- Evidence changes invalidate affected selections.
- Selection never grants statement verification, approval, or export eligibility.

The primary SRS requirements are Req-Func-Sw-28,
Req-Func-Sw-29, and Req-Func-Sw-30.