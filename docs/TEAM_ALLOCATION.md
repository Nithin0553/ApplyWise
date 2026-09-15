# ApplyWise Team Allocation

**Status:** Initial development allocation  
**Date:** 2026-09-15  
**Project Manager:** Nithin Thirumani (`@Nithin0553`)

This allocation is designed to let all six developers work in parallel while minimizing shared-file ownership and respecting the precedence in the Project Vision Document. The team should not attempt all sixteen features simultaneously. The first development tranche focuses on foundations and early contracts/prototypes.

## Team identities

| Team member | GitHub | Project role |
|---|---|---|
| Nithin Thirumani | `@Nithin0553` | Project Manager |
| Niraali Deepak Bandi | `@niraalibandi` | Project Technical Manager |
| Sampreet Ajjanagouda Patil | `@Sampreet26` | Project Requirements Manager |
| Daniel Hernandez | `@dhernandez23` | Project Design Manager |
| Suraj Loni | `@surajloni` | Project Test Manager / Quality Assurance Manager |
| Prudhvi Prasad Sikharam | `@Prasad04ad`* | Project Configuration Manager |

\* `@Prasad04ad` should be re-confirmed before CODEOWNERS enforcement because the current GitHub connection did not resolve repository permission information for that username.

## Initial parallel work allocation

### Nithin — F02/F13 integration anchor

**Primary first task:** F02 Career Evidence Profile domain contract and core data model.  
**Secondary early task:** define the F13 job/application/resume-version snapshot model before full F13 implementation.

Owned areas:
- `apps/api/app/modules/evidence/`
- `apps/api/app/modules/applications/` for the early version-model contract
- `apps/web/src/features/evidence/`
- `apps/web/src/features/applications/`

Reason: the evidence model is the trusted source for matching, generation, and verification, and the vision requires the F13 version model to be defined early.

### Niraali — F07 generation/provenance technical lane

**Primary first task:** F07 AI Statement Generation with Provenance contract/prototype.

Owned areas:
- `apps/api/app/modules/generation/`
- `apps/api/app/services/ai/`
- `apps/web/src/features/tailoring/`

Responsibilities include the provider abstraction, grounded-generation request/response contract, provenance output contract, and technical review of cross-module interfaces.

### Sampreet — F04 job-analysis lane

**Primary first task:** F04 Job Description Analysis contract/prototype.

Owned areas:
- `apps/api/app/modules/job_analysis/`
- `apps/web/src/features/job-analysis/`

The first deliverable is a normalized requirement contract covering required/preferred skills, experience, education, responsibilities, importance, and source text spans where practical. F05/F06 will follow after this contract stabilizes.

### Daniel — F10 document/UI lane

**Primary first task:** F10 Resume Generation, Templates, and Export architecture/contract plus the shared frontend shell needed by later feature pages.

Owned areas:
- `apps/api/app/modules/documents/`
- `apps/web/src/features/resume/`
- shared frontend component work only when explicitly identified in the issue/PR

F10 implementation must not bypass F08/F09. Until verification and approval are available, Daniel should use fixtures/mocks for approved statements rather than directly consuming AI output.

### Suraj — F08 verification/quality lane

**Primary first task:** F08 Claim Verification contract/prototype and adversarial verification test corpus.

Owned areas:
- `apps/api/app/modules/verification/`
- `apps/web/src/features/verification/`
- verification-specific fixtures/tests

The first contract must support `VERIFIED`, `INFERRED`, and `UNSUPPORTED`, explicitly detect unsupported numerical claims, and make unsupported content ineligible for export. F09 follows this lane after the verification contract stabilizes.

### Prudhvi — F01 authentication/configuration lane

**Primary first task:** F01 User Registration and Authentication / RBAC foundation.

Owned areas:
- `apps/api/app/modules/auth/`
- `apps/web/src/features/auth/`
- auth-related environment/configuration changes approved through normal review

Server-side ownership and role checks are mandatory. Reviewer and Administrator permissions must remain distinct from Job Seeker ownership.

## Next feature ownership after the first tranche

The following is the planned continuation, subject to review after the first integration checkpoint:

| Owner | Planned follow-on features |
|---|---|
| Nithin | F13 full Resume Version Management and Application Tracking; F14 coordination/integration |
| Niraali | F07 completion; F11 Cover Letter Generation; F15 Interview Defensibility Check |
| Sampreet | F05 Requirement-to-Evidence Matching and Gap Analysis; F06 Content Selection Engine; support F16 requirement taxonomy |
| Daniel | F10 completion; F12 Resume Formatting and ATS Readability Analysis |
| Suraj | F09 Statement Review and Approval; cross-feature verification/security/quality tests |
| Prudhvi | F01 completion; F03 Resume Import/Profile Population infrastructure with evidence-owner review |

F16 Market Skill Demand Analysis is low priority and will be assigned only after the first integration boundary is stable; its likely owners are Sampreet for requirement/taxonomy logic with Nithin coordinating product integration.

## Integration rule

No member may directly depend on another member's internal database tables or implementation classes. Cross-team dependencies use documented contracts, fixtures, or APIs. A shared contract change must be called out in the PR description and reviewed by the Technical Manager.

## First integration checkpoint

The team should integrate in this order:

1. F01 ownership/auth foundation + F02 approved-evidence model + F13 snapshot model.
2. F04 normalized requirements.
3. F07 generation with provenance using approved evidence fixtures.
4. F08 verification of generated claims.
5. F09 user approval.
6. F10 export from approved statements and F13 save/version linkage.

The first release boundary remains: an evidence-grounded, verified, user-approved resume that can be exported and saved as a version linked to the related application.
