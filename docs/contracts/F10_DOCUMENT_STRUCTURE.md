# F10 structured resume document — issue #85

## Trusted input

`build_resume_document` accepts only content supplied by
`TrustedFinalizationService.current_export_content`. It does not itself grant
export authorization. F13 includes F02 `start_date`, `end_date`, `skill_name`
and `credential` in its immutable evidence snapshot and freshness comparison.

## Document contract

`ResumeDocument` contains header context (`full_name`, `target_role`, `company`),
`template` (`standard` or `compact`), and nonempty `sections`.
Each section has a heading and nonempty entries. Each entry carries:

- `evidence_ids` and `statement_ids` for provenance;
- `title`, `organization`, `role`, `start_date`, `end_date` from approved evidence;
- exact approved statement strings, without rewriting.

Skill titles use `skill_name` when present; certification titles use `credential`.
Other titles come from the evidence title. See ADR-004 for section mapping,
multi-source statements, the no-summary decision, and legacy-version behavior.

## HTTP boundary

- `GET /api/documents/resume-versions/{id}/preview?template=standard`
  returns the structured document JSON.
- `GET /api/documents/resume-versions/{id}/export?format=pdf&template=standard`
  returns the rendered PDF or DOCX attachment.

Both require the authenticated Job Seeker and the same current ownership,
verification, approval, revision and evidence checks. Anonymous requests return
401, foreign/missing versions 404, ineligible/stale versions 409, and unavailable
verification 503. A successful preview does not authorize a subsequent export.

## Scope

Career sections contain only evidence supporting selected finalized statements.
Unselected approved profile records are not automatically added. Resume Studio
uses this API instead of sample content. The separate pre-finalization guided
journey review and historical-version viewer remain draft/history interfaces.
