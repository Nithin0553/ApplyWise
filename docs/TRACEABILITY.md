# Feature Traceability Foundation

**Last updated:** 2026-10-01

Statuses below reflect repository-visible implementation state. A feature marked implemented in an
open PR is not yet part of `main` until that PR is merged.

| Feature | Priority | Precedence | Requirements | Tests | Status |
|---|---|---|---|---|---|
| F02 Career Evidence Profile | High | 1 Foundations | Issue #2 / F02 contract | Backend persistence/domain + contract tests | Implemented in PR #8; pending merge |
| F08 Claim Verification | High | 3 Controlled Generation; prototype early | TBD | TBD | Not started in repository |
| F09 Statement Review and Approval | High | 3 Controlled Generation | TBD | TBD | Not started in repository |
| F01 User Registration and Authentication | High | 1 Foundations | Issue #7 | TBD | Assigned; integration dependency for F02/F13/F14 |
| F07 AI Statement Generation with Provenance | High | 3 Controlled Generation | Issue #3 | Owner branch tests | In progress on `feat/F07-grounded-generation` |
| F04 Job Description Analysis | High | 2 Job Analysis | TBD | TBD | Not started in repository |
| F05 Requirement-to-Evidence Matching and Gap Analysis | High | 2 Job Analysis | TBD | TBD | Not started in repository |
| F06 Content Selection Engine | High | 2 Job Analysis | TBD | TBD | Not started in repository |
| F10 Resume Generation, Templates and Export | High | 4 Usable Application | Issue #5 | TBD | Assigned; integration dependency for F13/F14 |
| F13 Resume Version Management and Application Tracking | High | model early / stage 4 | Issue #10 / F13 contract | Backend persistence/domain + frontend component tests | Implemented in PR #8; pending merge |
| F03 Resume Import and Profile Population | Medium | 5 Extensions | TBD | TBD | Not started in repository |
| F12 Resume Formatting and ATS Readability Analysis | Medium | 5 Extensions | TBD | TBD | Not started in repository |
| F11 Cover Letter Generation | Medium | 5 Extensions | TBD | TBD | Not started in repository |
| F14 Peer Review and Sharing | Medium | 5 Extensions | Issue #12 / F14 contract | Backend persistence/security + frontend component tests | Foundation implemented in PR #8; F01/F10 wiring pending |
| F15 Interview Defensibility Check | Low | 5 Extensions | TBD | TBD | Not started in repository |
| F16 Market Skill Demand Analysis | Low | 5 Extensions | TBD | TBD | Not started in repository |

The first integration-release boundary remains an evidence-grounded, verified, user-approved
resume that can be exported and saved as a version linked to the related application.

F02 now provides the approved-evidence boundary, F13 provides immutable application-linked resume
versions, and the F14 foundation provides controlled version-specific sharing. The remaining
release-critical seams are F01 authenticated identity/RBAC, F04-F09 job-analysis-to-approval flow,
and F10 approved document rendering/export.
