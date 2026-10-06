# Feature Traceability Foundation

**Last updated:** 2026-10-02

Statuses below reflect repository-visible implementation state. Work in an open PR is not part of
`main` until that PR is merged.

| Feature | Priority | Precedence | Requirements | Tests | Status |
|---|---|---|---|---|---|
| F02 Career Evidence Profile | High | 1 Foundations | Issue #2 / F02 contract | Backend persistence/domain + contract tests | Implemented in PR #8; F01 integration in progress |
| F08 Claim Verification | High | 3 Controlled Generation; prototype early | TBD | TBD | Not started in repository |
| F09 Statement Review and Approval | High | 3 Controlled Generation | TBD | TBD | Not started in repository |
| F01 User Registration and Authentication | High | 1 Foundations | Issue #7 | Backend auth/RBAC + frontend auth tests | Merged to `main` in PR #13 |
| F07 AI Statement Generation with Provenance | High | 3 Controlled Generation | Issue #3 | Owner branch tests | Implemented in PR #11; pending integration/merge |
| F04 Job Description Analysis | High | 2 Job Analysis | Issue #4 | Parser/API/frontend prototype tests | Implemented in PR #15; pending merge |
| F05 Requirement-to-Evidence Matching and Gap Analysis | High | 2 Job Analysis | TBD | TBD | Not started in repository |
| F06 Content Selection Engine | High | 2 Job Analysis | TBD | TBD | Not started in repository |
| F10 Resume Generation, Templates and Export | High | 4 Usable Application | Issue #5 | Frontend prototype tests | UI prototype in PR #14; document/export work remains |
| F13 Resume Version Management and Application Tracking | High | model early / stage 4 | Issue #10 / F13 contract | Backend persistence/domain + frontend component tests | Implemented in PR #8; F01 integration in progress |
| F03 Resume Import and Profile Population | Medium | 5 Extensions | TBD | TBD | Not started in repository |
| F12 Resume Formatting and ATS Readability Analysis | Medium | 5 Extensions | TBD | TBD | Not started in repository |
| F11 Cover Letter Generation | Medium | 5 Extensions | TBD | TBD | Not started in repository |
| F14 Peer Review and Sharing | Medium | 5 Extensions | Issue #12 / F14 contract | Backend persistence/security + frontend component tests | Foundation in PR #8; F01 role wiring in progress |
| F15 Interview Defensibility Check | Low | 5 Extensions | TBD | TBD | Not started in repository |
| F16 Market Skill Demand Analysis | Low | 5 Extensions | TBD | TBD | Not started in repository |

The first integration-release boundary remains an evidence-grounded, verified, user-approved
resume that can be exported and saved as a version linked to the related application.

F01 now supplies authenticated identity/RBAC. F02 supplies the approved-evidence boundary, F13
supplies immutable application-linked resume versions, and F14 supplies controlled
version-specific sharing. The remaining release-critical seams are F04-F09 job-analysis-to-approval
integration and F10 approved document rendering/export.
