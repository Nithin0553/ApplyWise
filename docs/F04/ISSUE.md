# F04 Job Description Analysis contract and prototype

Intended owner: @Sampreet26

## Scope
Define and prototype F04 so a supplied job description is transformed into normalized requirements that downstream matching consumes without depending on parser internals.

## Acceptance criteria
- Cover skills, education, experience, responsibilities and role-specific qualifications.
- Represent Critical, Preferred and Optional importance; flag ambiguity for review.
- Preserve exact source text and explain extraction context.
- Reject empty and malformed descriptions with clear validation errors.
- Test representative postings and ambiguous requirements.
- Allow F05/F06 to consume public DTOs/JSON Schema without parser implementation imports.

## Branch
`feat/F04-job-analysis`

## Dependencies and review
Technical review of the versioned contract and null importance for ambiguous requirements. F01 route integration is a subsequent task; the current demo runs locally. The Vite proxy/demo-entry change needs configuration review.
