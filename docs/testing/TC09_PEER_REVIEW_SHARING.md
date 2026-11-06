# Supplemental / Deferred STD Case — Original TC-9: Share Resume for Review

**Test case:** Original TC-9 (deferred; excluded from the eight-case STD submission) | **Issue:** #39 | **Responsible author:** @Nithin0553 | **Execution status:** Prepared, not executed  
**Feature:** F14 Peer Review and Sharing; immutable F13 version handoff; F01 role-based access  
**Traceability:** `docs/contracts/F14_PEER_REVIEW_SHARING.md`, `docs/contracts/F13_SNAPSHOT_CONTRACT.md`, F14 service, router, and integration tests.  
**Approved SRS traceability:** PVD/SRS version 3.0 (09/25/2026), Appendix A: Req-Func-Sw-78–84 (F14), Req-Qual-Sec-1, Req-Qual-Sec-2, Req-Qual-Sec-5, plus Req-Func-Sw-1–5 (F01 reviewer authentication and role access). Confirm exact citation formatting in the final professor STD template.  
**Duration estimate:** 35–55 minutes plus environment setup.  
**Target application version:** Record git commit SHA/URL and API version at execution.  
**Test hardware/software:** Record OS, browser/version, RAM/device, API service build and isolated database details at execution; no unverified test environment is claimed.  
**Test accounts/data:** Synthetic Job Seeker A (owns application/resume version v1 and v2), Job Seeker B (foreign owner), authorized Reviewer R, and a separate unprivileged role. Use test tokens, never production credentials.  
**Result column:** N/A means planned and **not executed**.

| Step | Exact action/test data | Expected outcome | Result |
|---|---|---|---|
| 1 | Sign in as A and list A's resume versions for application A1 | HTTP 200; versions belong to A1 and retain immutable version IDs | N/A |
| 2 | POST `/api/shares/resume-versions/{v1_id}` as A with future expiration | HTTP 201; response contains grant and one-time opaque secret; share references only v1 | N/A |
| 3 | Confirm share storage via authorized test-service inspection (redact secret) | Only a SHA-256 digest is persisted; raw secret is not stored in F14 share record | N/A |
| 4 | List A's shares through GET `/api/shares/` | HTTP 200; newly created grant appears, expiration and version ID match | N/A |
| 5 | Attempt to create a share for A's v1 using B token | HTTP 404; no foreign version or grant details disclosed | N/A |
| 6 | Attempt owner-only share listing with Reviewer R | Authorization denied; no A-owned grants returned | N/A |
| 7 | Authenticate as R and resolve A's valid secret | HTTP 200; returns only share ID, version ID, creation and expiration metadata; no career profile or full snapshot | N/A |
| 8 | Resolve invalid/random 20–200 character secret as R | HTTP 404 indistinguishable from revoked/expired secret | N/A |
| 9 | POST synthetic comment `"Please clarify the API testing scope."` as R using valid secret | HTTP 201; feedback tied to exactly the v1/share and reviewer identity | N/A |
| 10 | List feedback as A for the share | HTTP 200; same comment appears in insertion order and F13 v1 remains unchanged | N/A |
| 11 | Attempt feedback with unprivileged role or missing token | Authorization denied; feedback count unchanged | N/A |
| 12 | Revoke share as A via POST `/api/shares/{share_id}/revoke`; repeat | HTTP 200; revoked state recorded; repeated revocation remains idempotent | N/A |
| 13 | Resolve revoked secret and try adding new feedback as R | Both requests return generic HTTP 404; pre-existing feedback stays in owner's history | N/A |
| 14 | Create a separate grant with valid future expiration; control clock after expiration; resolve | Expired share denied with same not-found behavior as invalid secret | N/A |
| 15 | Create v2 grant; resolve using v2 and compare to v1 link | Each share identifies exactly its own immutable resume version; no cross-version leakage | N/A |
| 16 | Attempt invalid/blank/oversized reviewer secret, test API input constraints | HTTP 422 for bounds violations, no content disclosed; use correct contract for tested build | N/A |

## API contract gate

PR #24 is merged into `main`; the active reviewer operations are `POST /api/shares/reviewer/resolve` and `POST /api/shares/reviewer/feedback` with the 20–200-character secret in the validated JSON request body, not the URL. PR #19's sharing UI was subsequently merged. At execution, verify the installed build and use **only its deployed endpoints**. Never expose a share secret in screenshots, URLs or logs.

**Submission mapping:** The approved reduced eight-case STD selection uses original cases 1, 2, 4, 5, 7, 11, 13 and 16. Original case 9 is **not selected**; keep this as a supplemental F14/issue #39 test plan, not as one of the eight executed case records.

**Blocked/not yet full product coverage:** The final F10-rendered resume reviewer view is not integrated, so a metadata-only reviewer resolution is not proof of a complete document-sharing UX.

## Test evidence / closure requirements

Capture test data identifiers, redacted HTTP transcripts, review role status, versions/grants, immutable version comparison, timestamps, defects, environment, actual elapsed time, and reviewer sign-off. Verify the requirement mapping, deferred-case designation and professor STD-template metadata before marking this appendix ready for submission. **No Pass/Fail outcomes are asserted without execution.**
