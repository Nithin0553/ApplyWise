# F04: add job analysis contract and local parser prototype

ApplyWise needs structured, source-linked job requirements before F05/F06 can implement matching. This change adds a versioned public contract and a deterministic English parser prototype, with a local review screen.

## Changes
- Public DTOs and JSON Schema for requirement categories, importance, experience and source spans.
- Rule-based extraction with exact source offsets and review flags for ambiguity.
- Clear input validation and a standalone local FastAPI demo endpoint.
- Feature-owned review screen with source context and JSON download.
- Representative fixtures, API/unit tests, frontend interaction tests and consumer documentation.

## Contract decisions
Importance is null when unstated or contradictory; downstream consumers must review these cases. Alternative qualifications remain in one clause. One clause may have multiple categories. IDs are stable within a document revision, not across text edits.

## Integration boundary
The router is not exposed through the production app until F01 authentication is integrated. The only shared configuration edit adds a Vite localhost proxy and standalone demo entry. No F13 work is part of this PR.

## Validation
See docs/F04/VALIDATION.md for executed checks. Follow docs/F04/README.md to reproduce the local demonstration.

## Review required
Review the DTO/JSON Schema with F05/F06 consumers and the Technical Manager. Review the shared Vite configuration with the Configuration Manager. Attach this PR to the existing F04 issue using GitHub's Development section. This is an initial prototype, not a production-ready parser.
