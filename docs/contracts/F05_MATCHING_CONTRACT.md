# F05 Requirement-to-Evidence Matching Contract

Status: Proposed contract for team review.
Owner: Sampreet Ajjanagouda Patil (@Sampreet26).

F05 compares normalized job requirements from F04 with the job seeker's approved career evidence from F02. It identifies supporting evidence, explains each match, and distinguishes presentation gaps from gaps requiring additional qualifications or experience.

This document defines the intended integration contract. It does not establish that the matching implementation is complete.

## Input boundaries

F05 consumes the public F04 requirement contract rather than importing parser implementation classes. Each requirement retains its ID, text, categories, importance, supporting source context, and any experience expectations or review flags.

F05 obtains evidence through the F02 service contract. It uses
`ApprovedEvidenceProvider.list_approved(user_id=...)` or
`list_grounding_contexts(user_id=...)`, depending on the adapter's needs.
It must not query the evidence persistence model directly.

Matching must consider the structured evidence fields relevant to the requirement, including skills, proficiency, credentials, education, roles, responsibilities, and dates. The description field alone is not the complete evidence record.

## Authentication and ownership

At the HTTP boundary, F01 supplies the authenticated Job Seeker identity. F05 uses that identity when requesting approved evidence from F02.

A caller-supplied user ID must not override the authenticated identity. Evidence belonging to another user must not appear in matching results or explanations.

Reviewer and Administrator permissions do not automatically grant access to a Job Seeker's private matching workflow.

## Support classifications

Each analyzed requirement receives one of these classifications:

- Strongly Supported: Approved evidence directly supports the stated requirement, including any explicit qualification or experience constraint.
- Partially Supported: Approved evidence supports part of the requirement, but a stated condition remains unmet or insufficiently documented.
- Unsupported: No available approved evidence supports the requirement.

These classifications describe support in the available evidence. Unsupported does not establish that the user lacks the qualification in real life.

Keyword overlap alone is insufficient to establish strong support. Matching must not invent experience duration, proficiency, credentials, achievements, or numerical outcomes.

## Matching result

The proposed result contains the source F04 document ID and one match entry for each requirement, preserving the original requirement order.

Each match entry includes:

- The original requirement ID.
- The support classification.
- References to the approved evidence records used.
- The approval timestamp associated with each evidence reference.
- An explanation connecting the classification to specific evidence.
- Any unmet conditions or missing evidence.
- A gap assessment and any review warnings.

An Unsupported result has no supporting evidence references. A partially supported result identifies both the supported portion and the unresolved conditions.

F05 must preserve the distinction between requirement importance and evidence support. A Critical requirement can still be Unsupported.

## Ambiguous requirements

F05 preserves F04 review flags and warnings. It must not silently resolve conflicting priorities, interpret "Python or Java" as requiring both languages, or invent missing experience thresholds.

Where ambiguity prevents a confident assessment, the result includes a review warning and explains the limitation. Any assigned support classification must remain grounded in the requirement text and available evidence.

## Gap analysis

F05 distinguishes gaps that may be addressed by presenting existing approved facts more clearly from gaps requiring additional qualifications or experience.

A presentation gap requires relevant approved evidence that already supports the underlying fact. Rewording must not create a qualification or experience that the evidence does not contain.

When the available evidence cannot establish which type of gap applies, F05 identifies the uncertainty and requests user review rather than making a definite claim.

For example, approved evidence describing a Docker tutorial may partially support a requirement for production Docker experience. The explanation must identify the limitation rather than imply that tutorial work establishes production experience.

## Approval changes and stale results

Evidence approval applies to its current content. F02 returns an approved record to UNCONFIRMED when its editable content changes and clears its approval timestamp.

F05 obtains current approved evidence for each new matching operation. Previously stored matching results must not be treated as current after their supporting evidence changes.

Before F06 uses a previous matching result, the integration must revalidate its evidence references against F02 and recompute affected matches when approval or content has changed. Deleted or unconfirmed records are no longer eligible support.

## Downstream use by F06

F06 consumes the documented matching output and current approved evidence references. It does not depend on F05's internal matching implementation.

F05 provides requirement-level support and gap explanations. F06 owns evidence ranking and content selection within resume template limits.

A strong match does not approve a generated statement or make it eligible for export. Statement verification and user approval remain the responsibilities of F08 and F09.

## Validation and failure behavior

Malformed requirement data, duplicate requirement IDs, and unsupported contract versions produce clear validation errors rather than partial success.

An empty approved-evidence collection is a valid input. Every supplied requirement is classified as Unsupported, with an explanation that no approved evidence is available.

An F02 retrieval failure must be reported as a failure. It must not be converted into an empty evidence collection or a successful result containing Unsupported matches.

No matching operation modifies the user's evidence, approval state, or original job requirements.

## Acceptance checks

The implementation must demonstrate that:

- Only the authenticated user's approved evidence is used.
- Strongly Supported, Partially Supported, and Unsupported results include appropriate explanations.
- Structured qualifications and experience constraints affect classification.
- Ambiguous requirements retain their review warnings.
- Unconfirmed, deleted, or stale evidence is not used as current support.
- Empty evidence and evidence-service failures produce different outcomes.
- F06 can consume the public matching contract without importing matching internals.

The SRS requires at least 90% labeling accuracy against human annotations for a sample of requirement-to-evidence pairs. The evaluation dataset, annotations, sample size, and measured result must be recorded before claiming that this target is met.