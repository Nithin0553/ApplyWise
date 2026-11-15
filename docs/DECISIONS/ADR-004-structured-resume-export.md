# ADR-004: Structured, evidence-backed resume exports

Status: Proposed in issue #85 implementation; requires team review.

## Decision

Use issue #85's option three: omit the summary in this version. There is no
approved summary evidence type or persisted user-authored summary contract.
Do not generate a motivation paragraph or convert onboarding preferences into
verified career claims. A user-authored summary can be added in a separate
change once its storage, attribution, and verification scope are agreed.

## Structure and grounding

F13 snapshots retain F02 start_date, end_date, skill_name, and credential in
addition to the existing evidence type, title, organization, role and approval
timestamp. F10 maps only evidence referenced by the finalized statements into
Experience, Education, Skills, Certifications, Projects or Additional Experience.
Empty sections are omitted. Each entry retains evidence IDs and statement IDs.
Metadata comes directly from approved F02 records; no employer, date or degree
is inferred from statement text. Account name and target job remain header
context, not F08-verified career evidence.

Statements citing multiple records appear once in Additional Qualifications,
with all evidence IDs, rather than assigning a combined claim to one employer.
The individual records still appear in their corresponding sections. Records
with identical employer names remain distinct: there is no reliable employment
parent ID with which to merge them safely. Missing dates are omitted; a missing
end date never asserts "Present" employment.

## Shared preview and export

Resume Studio loads the structured document through the authenticated preview
endpoint. Preview, PDF and DOCX use the same adapter and the same current F13
validation. Download performs fresh validation even after a successful preview.
Both file formats consume a common ordered content sequence.

The guided journey's pre-finalization candidate review is a separate draft
interface, not the validated Resume Studio preview. Its local draft/text export
flow is outside this change.

## Compatibility

The new snapshot fields default to null when reading old JSON; no database
migration or historical snapshot rewrite is required. If an old snapshot lacks
metadata that is now present in F02, exact-content validation rejects it as
stale. Finalize a new version after current verification and approval. Never
silently enrich an old approved version or relax the current-state comparison.

## Validation

`test_document_structure.py` covers section content parity in PDF/DOCX, empty
sections, unselected evidence, multi-source claims, unknown end dates, F02 to
F13 to F10 metadata, stale metadata, and preview authorization/revocation.
Existing real-provider end-to-end export tests remain in place. Resume Studio
tests cover actual content, failed preview, and late responses after selection.
