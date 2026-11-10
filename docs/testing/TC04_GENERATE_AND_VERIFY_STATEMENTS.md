# STD Appendix — TC-4: Generate and Verify Resume Statements (submitted as TC-3)

**Test case:** original TC-4 in the sixteen-case Section 5.1 list; submitted as **TC-3** in the reduced eight-case STD | **Issue:** #34 | **Responsible author:** @niraalibandi | **Status:** Prepared / not executed  
**Scope:** the F07 statement generation and F08 claim verification interface — provenance from approved evidence, classification as VERIFIED / INFERRED / UNSUPPORTED, and detection of unsupported numerical claims.  
Approved SRS traceability: ApplyWise Software Requirements Specification, version 3.0, dated 09/25/2026, Appendix A. Req-Func-Sw-31 through Req-Func-Sw-36 (F07 AI Statement Generation with Provenance); Req-Func-Sw-37 through Req-Func-Sw-42 (F08 Claim Verification); Req-Func-Sw-6 through Req-Func-Sw-12 (F02 Career Evidence Profile, as the source of the approved evidence under test); Req-Qual-Trace-1, which requires a verification state on every generated statement; Req-Qual-Trace-2, which blocks statements classified Unsupported from export; Req-Qual-Trace-3, covering provenance and approval; and Req-Qual-Sec-1, which requires authorization and ownership to be enforced on the server. No identifier in this appendix is invented. No numerical accuracy target is claimed either: Req-Qual-Match-3 states a labelling accuracy goal for requirement-to-evidence matching, which belongs to F05 and is outside the scope of this case.  
**References:** `docs/contracts/F07_GENERATION_CONTRACT.md`, `docs/contracts/F08_CLAIM_VERIFICATION_CONTRACT.md`, `docs/contracts/F02_EVIDENCE_CONTRACT.md`, `docs/testing/STD_SUBMISSION_CASE_MAP.md`.  
**Planned duration:** 45–60 minutes, plus environment setup.  
**Software under test:** ApplyWise API 0.1.0, `main`, commit `5d75121`. Record the exact commit and deployment identifier at execution.  
**Support software / hardware:** Python 3.13, pytest, an HTTP client, PostgreSQL 16 or an isolated SQLite database, a current desktop browser; one standard laptop or workstation, no special equipment. Record exact versions, OS and device at execution.

Test environment and data: one synthetic job seeker account A, and a second account B used only to demonstrate owner isolation. Account A holds one approved work-experience record titled "Associate QA Engineer" at "Model N", described as "Built and maintained automated regression suites for revenue management software.", and one further record that is created and deliberately left unconfirmed. The target job context is "Software Engineer in Test", requiring Python and test automation. All accounts, evidence and credentials are synthetic and no real personal data is used. Record the database state, operating system, browser and version at the time of execution.

Result notation: N/A means the step is planned and has not been executed. A step is recorded as Pass or Fail only after it has been executed in a recorded environment, with the observed outcome noted alongside it. A step that cannot be executed because a capability is unavailable is recorded as not executed, and never as Pass.

This appendix records the detailed test case for the interface between F07 AI statement generation and F08 claim verification. Original case TC-4 in the sixteen-case Section 5.1 list is submitted as TC-3 under the approved reduced eight-case numbering; both identifiers are given so that the appendix can be cross-referenced against either list. Every expected outcome stated below was confirmed against the merged implementation at commit 5d75121 before this appendix was written, so the outcomes describe the behaviour the system actually produces rather than the behaviour it is intended to produce. The Result column nevertheless remains N/A throughout, because no step has yet been executed manually in a recorded test environment, and automated coverage is not equivalent to a documented manual execution.

## Metadata

| Field | Value |
|---|---|
| Test Case ID | TC-4 (sixteen-case Section 5.1 list); submitted as TC-3 |
| Test Case Name | Generate and Verify Resume Statements |
| Brief Description | This test case verifies the interface between F07 AI statement generation and F08 claim verification. It confirms that generated statements carry provenance back to approved evidence owned by the signed-in user, that generated output is never presented as verified or approved, that F08 classifies each claim as VERIFIED, INFERRED or UNSUPPORTED, that unsupported numerical claims are detected and barred from export, and that a change to the supporting evidence invalidates an existing verification result. |
| Priority | High |
| Planned Test Duration | 45 to 60 minutes, plus environment setup |
| Current Version | 1.0 |
| Date of First Version | 11/09/26 |
| Date of Current Version | 11/10/26 |
| Created By | Niraali Deepak Bandi |
| Last Update By | Niraali Deepak Bandi |
| Approved By | Project manager technical review pending; approval applies to the test plan, not execution |
| The version of Software Under Test | ApplyWise API 0.1.0, main branch, commit 5d75121. Record the exact commit and deployment identifier again at execution. |
| Test Engineer to Conduct the Test | To be assigned and recorded before manual execution |
| List of Test Support Software | Python 3.13, pytest, an HTTP client such as the FastAPI test client, Postman or curl, PostgreSQL 16 or an isolated SQLite database, and a current desktop browser. Record exact versions at execution. |
| List of Test Support Hardware | One standard laptop or workstation able to run the API and a browser. No special equipment is required. Record the operating system, device and available memory at execution. |

## Test steps

| Step | Input / action | Exact expected outcome | Result |
|---|---|---|---|
| 1 | Sign in as job seeker A. Create one work-experience evidence record and approve it through the F02 evidence route. Create a second record and leave it unconfirmed. | Both records are stored under account A. The first reports status approved. The second remains unconfirmed and is therefore not eligible to ground generated content. | N/A |
| 2 | Request F07 generation for the target job context, selecting only the approved evidence identifier, with max_statements set to 5. | HTTP 200. The response contains at least one candidate statement. Every statement carries status CANDIDATE, verification_status PENDING, approval_status UNREVIEWED and export_eligible false, so generated text is never presented as verified or approved. | N/A |
| 3 | Inspect the evidence identifiers attached to each returned statement. | Every statement cites only identifiers supplied in the request, and every cited identifier belongs to account A. No statement is returned without at least one citation. | N/A |
| 4 | Repeat the generation request using the demo provider, which emits one fabricated citation and one uncited statement on every run. | HTTP 200. The fabricated and uncited outputs appear in the rejected list, with reasons naming an unknown evidence reference and an absence of cited evidence. Neither appears among the accepted statements. | N/A |
| 5 | Request generation twice more: once citing the unconfirmed evidence record, and once citing a randomly generated identifier that does not exist. Compare the two responses. | Both requests return HTTP 404 with identical response bodies, so the reply cannot be used to learn whether an identifier exists. Neither request reaches the AI provider. | N/A |
| 6 | Submit generation requests with max_statements set to 0 and then to 11, which fall outside the documented range of 1 to 10. | Both requests are rejected with HTTP 422 before any generation occurs. | N/A |
| 7 | Submit to F08 a claim whose content is present in the approved evidence: "Built and maintained automated regression suites for revenue management software", citing the approved record. | HTTP 201. The claim is classified VERIFIED with export_eligible true, and the findings record that the claim's wording is fully covered by the cited evidence. | N/A |
| 8 | Submit to F08 an unsupported numerical claim: "Reduced regression runtime by 85%", citing the same approved record, where that figure appears nowhere in the evidence. | HTTP 201. The claim is classified UNSUPPORTED with export_eligible false. The findings include a figure-not-in-evidence reason quoting the figure 85%, so the user is told exactly which value is unsupported. | N/A |
| 9 | Submit to F08 a claim naming an organisation absent from the evidence: "Built automated regression suites at Google for revenue management software". | HTTP 201. The claim is classified UNSUPPORTED and the findings include an entity-not-in-evidence reason naming the organisation, so a fabricated employer is treated as fabrication rather than as wording. | N/A |
| 10 | Submit to F08 a claim that invents nothing but is worded beyond the evidence: "Improved release confidence for the billing organisation". | HTTP 201. The claim is classified INFERRED with export_eligible true. Inferred claims are not certified but are not blocked, so the decision to stand behind them remains the user's. | N/A |
| 11 | Submit an F08 request that additionally supplies a status field set to VERIFIED and a revision field of the caller's choosing. | HTTP 422. The request model forbids unknown fields, so a caller cannot assert its own verification outcome; the classification is always computed on the server. | N/A |
| 12 | Submit three boundary requests to F08: a claim whose text is only whitespace, a claim of 501 characters against the documented 500 character limit, and a request citing an empty evidence list. | All three are rejected with HTTP 422 and nothing is stored. | N/A |
| 13 | Unconfirm the approved evidence record supporting the VERIFIED claim from step 7, then read that claim from F08 again. | The claim is now classified UNSUPPORTED with export_eligible false, the findings record that the cited evidence is no longer approved, and the verification revision differs from the value recorded in step 7. A change to the supporting evidence therefore invalidates the earlier result without any manual revocation. | N/A |
| 14 | Sign in as job seeker B. Read the statement identifier created by account A in step 7, and separately read a randomly generated identifier that does not exist. | Both reads return HTTP 404 with identical response bodies, so a foreign statement cannot be distinguished from one that does not exist. | N/A |

## Evidence and closure requirements

Evidence and closure requirements: at execution, record the commit identifier and deployment of the software under test, the operating system, browser and version, the database state, the start and end times and the actual duration, the identifier of the engineer who executed the case, the observed outcome for every step, any defect reports raised, and the reviewer sign-off. Redacted HTTP transcripts are acceptable evidence for the API steps. Automated coverage for this interface exists in tests/test_generation_api.py, tests/test_verification_api.py, tests/test_verification_analysis.py and tests/test_f08_f09_integration.py, and may be cited as supporting evidence, but it does not substitute for the manual execution recorded here.

## Known limitations

Known limitations, recorded rather than implied: F08 compares a claim with its evidence lexically and does not detect paraphrase, so a quantity expressed in words rather than digits is not caught. Entity detection relies on capitalisation, so a lowercased organisation name is not caught. Only years are compared against evidence date ranges, not months or durations. No accuracy percentage is claimed for the classifier in this appendix, because none has been measured against a labelled sample.
