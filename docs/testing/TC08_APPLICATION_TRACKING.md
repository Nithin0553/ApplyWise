# STD Appendix — TC-8: Manage Resume Versions and Track Applications

**Test case:** TC-8 | **Issue:** #38 | **Owner:** @Nithin0553 | **Status:** Prepared / not executed  
**Scope:** F13 application tracking, immutable versions, user isolation, status lifecycle, and next action date.  
**Sources:** `docs/contracts/F13_APPLICATION_TRACKING.md`, `docs/contracts/F13_SNAPSHOT_CONTRACT.md`, `apps/api/app/modules/applications/router.py` and service/tests.  
**Approved SRS IDs:** **Pending verification against the approved SRS**; no unverified requirement identifiers are asserted here.  
**Version/build:** `main` commit SHA and environment build to be recorded at execution.  
**Environment:** Staging or test database with F01 authentication; record OS, browser/version, device and API deployment ID at execution.  
**Duration estimate:** 35–50 minutes, excluding provisioning and cleanup.  
**Prerequisites:** Two separate job-seeker accounts A/B, controlled F02 approved evidence, two eligible historical snapshots prepared through test fixtures. Use synthetic identities only.  
**Execution key:** All current Result entries are **N/A — not executed**; never infer a Pass from the existence of implementation or automated tests.

| Step | Input or action | Exact expected result | Result |
|---|---|---|---|
| 1 | Log in as A; GET `/api/applications/` with A token | HTTP 200; only A-owned application records returned | N/A |
| 2 | POST an application with company `Example Co`, role `Software Engineer`, status `draft` | HTTP 201; unique ID and matching company/role; owner resolves to A | N/A |
| 3 | GET new application by ID using A token | HTTP 200; same ID, stored draft status and metadata | N/A |
| 4 | PATCH job URL and notes; then GET application | HTTP 200; new URL/notes persisted, role and company unchanged | N/A |
| 5 | PATCH a `next_action_on` ISO date | HTTP 200; exact date stored; reload retains it | N/A |
| 6 | POST status `applied` with controlled `occurred_on` date | HTTP 200; status becomes `applied`; `applied_on` matches specified date | N/A |
| 7 | POST valid status `interviewing`, then `offer` | HTTP 200 for each; status history progresses without skipping owner checks | N/A |
| 8 | POST terminal `accepted`; then request `applied` | First HTTP 200 with `closed_on`; reversal HTTP 409 and remains accepted | N/A |
| 9 | POST a version containing two unique approved evidence IDs and two provenance-linked statements using the F13 snapshot contract (historical test record, **not** trusted final export) | HTTP 201; version 1; snapshot contains the submitted immutable content and owner/application/version references | N/A |
| 10 | POST another version for the same application, then list versions | HTTP 201; version 2; list ordered 1 then 2, both complete | N/A |
| 11 | Edit F02 source evidence or application notes after version creation, then fetch version 1 | Historical snapshot content remains unchanged | N/A |
| 12 | With B token, GET A's application and version; try POST version under A's ID | HTTP 404 for foreign-owned IDs; no A data disclosed or mutated | N/A |
| 13 | POST version with duplicate evidence/statement IDs, or citation to evidence outside snapshot | HTTP 422; no resume version created | N/A |
| 14 | PATCH dates where `closed_on` precedes `applied_on` | HTTP 422; original dates remain intact | N/A |
| 15 | In web Applications, expand record, change notes and next-action date, reload | Correct F13 record changes persist; resume version count remains correct | N/A |
| 16 | Interrupt a save or simulate an API 5xx before confirmation; reload list | UI reports failure and does not claim the version is saved; verify server state before retry | N/A |

**Evidence required when executed:** request/response capture with secrets redacted, application and version IDs (test-only), database or API readback screenshots, browser/device details, observed results, defect IDs and actual duration.

**Known limitations:** F13 stores historic snapshots but is **not** the F08/F09/F10 finalization trust boundary. Issue #22 remains open. A saved version alone is not proof of export eligibility. The UI's reviewed text file is not a final PDF/DOCX document.

**Review checklist:** Confirm SRS IDs and professor template fields; validate expected HTTP codes against deployment, collect peer review, and replace each N/A only after running that exact step.
