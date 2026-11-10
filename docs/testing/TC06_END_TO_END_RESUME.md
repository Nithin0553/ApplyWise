# STD Appendix — TC-6: Complete Tailored Resume Workflow (original case TC-11)

**Test case:** TC-6 in reduced eight-case submission (original TC-11) | **Issue:** #41 | **Responsible author:** @Nithin0553 | **Status:** Prepared / not executed  
**Scope:** F01 → F02 → F04/F05/F06 → F07 → F08 → F09 → F10 → F13, with negative tests for unsupported/unapproved claims.  
**Approved SRS traceability:** Version 3.0, 09/25/2026, Appendix A: Req-Func-Sw-1–5 (F01), 6–12 (F02), 18–22 (F04), 23–27 (F05), 28–30 (F06), 31–36 (F07), 37–42 (F08), 43–49 (F09), 50–58 (F10), 69–77 (F13), plus Req-Qual-Trace-1–4, Req-Qual-Match-1–2 and Req-Qual-Data-1. Confirm the final professor STD traceability table formatting before submission.  
**References:** `docs/FEATURE_BOUNDARIES.md`, `docs/contracts/F02_EVIDENCE_CONTRACT.md`, `F07_GENERATION_CONTRACT.md`, `F13_APPLICATION_TRACKING.md`, `docs/UI_RELEASE_INTEGRATION.md`.  
**Estimate:** 60–90 minutes after all integrations exist, plus setup; enter actual timing after execution.  
**Target build/environment:** Record commit SHA, backend deployment ID, DB state, operating system, browser/version, device and test account credentials redacted at execution.  
**Test data:** Synthetic new job seeker A, separate job seeker B, one approved work example (e.g. `"Built REST API tests in Python for a capstone project."`), one unconfirmed example, target role requiring API testing, and an unsupported numerical claim (`"Improved performance by 90%"`) not present in any evidence.  
**Result notation:** N/A = not executed; feature unavailable = blocked/not executed, never Pass.

| Step | Test action and input | Exact expected outcome | Result |
|---|---|---|---|
| 1 | Register new A with unique synthetic email and valid password; sign in | F01 creates isolated account, authenticated JWT session; no Demo Mode | N/A |
| 2 | Submit incomplete/invalid registration and wrong password | Form and API show meaningful errors; no signed-in session created | N/A |
| 3 | Complete six-step onboarding and select valid resume file (if importer available) | Answers persist according to product contract; imported content remains unconfirmed until review | N/A — not manually executed (F03 parser merged) |
| 4 | Create F02 work example `"Built REST API tests in Python"` via approved evidence route | New record stored under A, initially unconfirmed | N/A |
| 5 | Explicitly approve true evidence; leave second example unconfirmed | First evidence approved; second remains ineligible for grounding | N/A |
| 6 | As B, attempt to retrieve/use A's evidence ID | Owner isolation enforced; no data returned and no generation from foreign data | N/A |
| 7 | Paste target job description with API testing responsibilities and required Python | JD input saved for current workflow; extracted requirements correspond to source text | N/A |
| 8 | Request job analysis and evidence matching | Requirements and matching/gap report reflect approved evidence only, with missing requirements indicated | N/A — full F04–F06 integration pending |
| 9 | Request F07 grounded generation selecting approved evidence IDs | Draft candidate statements cite actual A-owned approved evidence IDs; provider output marked CANDIDATE, not approved | N/A |
| 10 | Attempt generation with only unconfirmed/foreign/missing evidence IDs | Server rejects selection without leaking ownership details | N/A |
| 11 | Feed verified-evidence-supported text into F08; compare explicit evidence claims | Deterministic verification classifies supported statement VERIFIED or appropriately INFERRED with correct provenance | N/A — not manually executed (F08 merged) |
| 12 | Submit unsupported claim `"Improved performance by 90%"` without evidence | Classification UNSUPPORTED and export-ineligible; no invented numerical value accepted | N/A — not manually executed (F08 merged) |
| 13 | In F09 review, deny unsupported claim and approve only supported statements | Denied claim removed from active resume; approved review state persisted and visible after refresh | N/A — not manually executed (F09 merged) |
| 14 | Try to approve without verification, or materially edit a VERIFIED claim | Export remains blocked until eligible/reverified per F08/F09 contract | N/A — not manually executed (F13 boundary merged) |
| 15 | Generate formatted resume preview from approved and export-eligible content | F10 previews expected sections; unsupported/unapproved text excluded | N/A — not manually executed (F10 merged) |
| 16 | Export PDF and DOCX from final approved version | Files download successfully, readable, text extracted matches approved statements | N/A — not manually executed (PDF/DOCX code merged) |
| 17 | Save final version linked to application A1 | F13 saves one immutable version with all evidence/provenance/verification/approval snapshots and correct application link | N/A — not manually executed (F13 path merged) |
| 18 | Edit evidence after version save, then reload earlier version | Historical snapshot is unchanged | N/A |
| 19 | Transition application to applied/interviewing and set next action | F13 stores legal lifecycle transition, dates and notes; version remains linked | N/A |
| 20 | Trigger interrupted save, generation service failure and invalid input | User sees actionable errors; no false confirmation; no corrupted/duplicate final versions | N/A |

## Implementation checkpoint and blockers (main branch, November 9, 2026; not production deployment)

| Capability | Current state in main | Impact on TC-6 |
|---|---|---|
| F01 authentication | Integrated | Testable |
| F02 evidence CRUD/approval | Integrated | Testable |
| F04/F05/F06 | Client-side requirement extraction and keyword-overlap preview | Not equivalent to full matching pipeline |
| F07 | Grounded scripted provider for candidate statements | Supports prototype review, not production-grade LLM |
| F08/F09 | Deterministic F08 provider and persisted F09 revision-bound approvals merged | Real API chain covered by automated integration tests; manual verification still required |
| F10 | Authenticated PDF/DOCX renderer and F13 current-state export gate merged | Requires live deployment and manual file/content validation |
| F13 | Applications, immutable versions and server-authorized trusted finalization merged | Historical drafts still do **not** authorize export |
| F14 | Version-scoped sharing is merged; final document rendering remains separate | Supplemental original TC-9, deferred from reduced STD |

**Evidentiary requirement (Nov 9, 2026):** F08, F09, F13 and F10 are merged, and automated real-provider API integration is proposed in PR #71 with 376 backend and 115 frontend tests passing on its head. This exercises actual PDF/DOCX output and stale/unsupported-claim denial, but is **not** the 20-step manual TC-6 execution. The F04–F06 full pipeline and live deployment still need scope assessment. Keep every manual result N/A until independently executed and evidenced.

**Review/execution fields to complete:** verify approved SRS ID ranges against the final professor STD template, project/version release, executed-by, executed-on date and start/end time, operating system/browser/hardware, test environment, observed outcomes, issue links, reviewers, evidence/attachment list, actual duration, and signature. Keep step result as N/A until that step is performed.
