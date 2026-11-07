# ApplyWise Team Allocation

**Status:** Current ownership (revised from initial development allocation)  
**Initial date:** 2026-09-15  
**Ownership update:** 2026-11-07  
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
| Prudhvi Prasad Sikharam | `@Pras04ad` | Project Configuration Manager |

## Initial parallel work allocation

### Nithin — F02/F13 integration anchor and F09 statement review owner

**Primary first task:** F02 Career Evidence Profile domain contract and core data model.  
**Secondary early task:** define the F13 job/application/resume-version snapshot model before full F13 implementation. **Current follow-on coding owner:** F09 Statement Review and Approval (issue #58) and its integration with F13 trusted finalization (issue #22).

Owned areas:
- `apps/api/app/modules/evidence/`
- `apps/api/app/modules/applications/` for the early version-model contract
- `apps/web/src/features/evidence/`
- `apps/web/src/features/applications/`

Reason: the evidence model is the trusted source for matching, generation, and verification, and the vision requires the F13 version model to be defined early.

### Niraali — F07 generation/provenance and F08 claim verification lane

**Primary first task:** F07 AI Statement Generation with Provenance contract/prototype.

Owned areas:
- `apps/api/app/modules/generation/`
- `apps/api/app/services/ai/`
- `apps/web/src/features/tailoring/`
- `apps/api/app/modules/verification/` (F08)
- `apps/web/src/features/verification/` (F08)

Responsibilities include the provider abstraction, grounded-generation request/response contract, provenance output contract, and technical review of cross-module interfaces. **Current added coding owner:** F08 Claim Verification (issue #6). F08 should consume server-authoritative approved F02 evidence and F07 candidates, classify VERIFIED/INFERRED/UNSUPPORTED, and supply an authenticated F09-consumable verification contract. Prioritize this core dependency now. F15 was delivered as a prototype in PR #62 (merged); its production route remains gated until trusted F09 approval is available.

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

### Suraj — non-coding QA and test coordination lane

**Current role:** Project Test/QA Manager; no implementation or other coding responsibilities. Suraj is **not** the owner of F08 or F09.

Owned non-coding responsibilities:
- Coordinate software test documentation, test-case readiness, execution tracking, defect reporting and quality reviews.
- Maintain review/QA sign-off notes, test evidence and documentation as appropriate; do not assign new code, automated-test coding, migrations or backend/frontend implementation.
- Existing STD documentation assignments (original TC-5, TC-13 and TC-16) remain non-coding QA tasks unless the team revises them separately.
- Liaise with Niraali (F08) and Nithin (F09) on verification quality, without blocking code ownership.

**Coding modules reassigned:** `apps/api/app/modules/verification/` verification logic → Niraali for F08; persisted review/approval service → Nithin for F09. Coordinate interface contracts and separate branches to prevent file collisions.

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
| Nithin | F13 full Resume Version Management and Application Tracking; F14 coordination/integration; **F09 persisted Statement Review and Approval** (#58) and F13 trusted finalization (#22) |
| Niraali | F07 completion; **F08 Claim Verification** (#6) as immediate core priority; F11 Cover Letter Generation; F15 Interview Defensibility Check delivered in PR #62 (prototype-gated until F09 integration) |
| Sampreet | F05 Requirement-to-Evidence Matching and Gap Analysis; F06 Content Selection Engine; support F16 requirement taxonomy |
| Daniel | F10 completion; F12 Resume Formatting and ATS Readability Analysis |
| Suraj | **No coding features.** Non-coding QA/test management, STD case documentation, manual test coordination, defect reporting and quality sign-off |
| Prudhvi | F01 completion; F03 Resume Import/Profile Population infrastructure with evidence-owner review |

F16 Market Skill Demand Analysis is low priority and will be assigned only after the first integration boundary is stable; its likely owners are Sampreet for requirement/taxonomy logic with Nithin coordinating product integration.

## Current F08/F09 handoff — November 6, 2026

The project manager has reassigned Suraj's **two remaining coding features** as one feature per developer. This overrides any older issue text, draft slide or initial allocation naming Suraj as the developer:

| Feature | New coding owner | Immediate deliverable | Depends on |
|---|---|---|---|
| **F08 — Claim Verification** | **Niraali** (`@niraalibandi`) | Backend authoritative verification, provenance, adversarial tests, verification contract (#6) | F02 owned approved evidence, F07 candidates |
| **F09 — Statement Review and Approval** | **Nithin** (`@Nithin0553`) | Authenticated persisted approval/rejection, invalidation on changed text/evidence, trusted reviewed-statement provider (#58) | F08 (#6) |
| **Suraj — Test / Quality Manager** | **Non-coding only** (`@surajloni`) | Test plans, manual case execution coordination, defect documentation and review/QA oversight | Works alongside F08/F09 owners; does not implement features |

**Dependency chain:** F02/F07 → F08 (Niraali) → F09 (Nithin) → F13 finalization (#22, Nithin) → F10 export (Daniel). Distinguish independent claim verification from the job seeker's decision to approve a statement. Client-supplied status flags and ordinary F13 user-reviewed draft snapshots are **not** F09 approval authority.

**Branch boundaries:** Niraali works in `feat/F08-claim-verification`, Nithin in `feat/F09-persisted-statement-review`. Agree on ID/status/revision contract first; avoid simultaneous edits to the same verification files. Both submit normal PRs with technical review and CI.

**Scheduling:** F08/F09 and finalization are required for the core trusted resume release. F15 was delivered in PR #62 (backend, UI, contract and tests) but is prototype-gated until F09 supplies trusted approved statements; in production its preview route is unavailable. F08 is the next coding priority. Do not describe F15 as integrated with production approvals or final export.

## Integration rule

No member may directly depend on another member's internal database tables or implementation classes. Cross-team dependencies use documented contracts, fixtures, or APIs. A shared contract change must be called out in the PR description and reviewed by the Technical Manager.

## First integration checkpoint

The team should integrate in this order:

1. F01 ownership/auth foundation + F02 approved-evidence model + F13 snapshot model.
2. F04 normalized requirements.
3. F07 generation with provenance using approved evidence fixtures.
4. **F08 verified claims — Niraali** (issue #6).
5. **F09 persisted, server-authoritative user approval — Nithin** (issue #58).
6. F10 export from approved statements and F13 save/version linkage.

The first release boundary remains: an evidence-grounded, verified, user-approved resume that can be exported and saved as a version linked to the related application.
