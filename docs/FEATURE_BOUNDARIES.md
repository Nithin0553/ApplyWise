# Feature Boundaries

| ID | Feature | Backend home | Frontend home | Main dependency |
|---|---|---|---|---|
| F01 | User Registration and Authentication | auth | auth | foundation |
| F02 | Career Evidence Profile | evidence | evidence | F01 |
| F03 | Resume Import and Profile Population | evidence | import | F02 |
| F04 | Job Description Analysis | job_analysis | job-analysis | F01 |
| F05 | Requirement-to-Evidence Matching and Gap Analysis | matching | matching | F02,F04 |
| F06 | Content Selection Engine | matching | tailoring | F05 |
| F07 | AI Statement Generation with Provenance | generation | tailoring | F02,F06 |
| F08 | Claim Verification | verification | verification | F02,F07 |
| F09 | Statement Review and Approval | verification | review | F08 |
| F10 | Resume Generation, Templates and Export | documents | resume | F09 |
| F11 | Cover Letter Generation | generation | cover-letter | F07,F08,F09 |
| F12 | Resume Formatting and ATS Readability Analysis | documents | ats | F10 |
| F13 | Resume Version Management and Application Tracking | applications | applications | F01; model early |
| F14 | Peer Review and Sharing | sharing | sharing | F10,F13 |
| F15 | Interview Defensibility Check | generation | interview | approved statements |
| F16 | Market Skill Demand Analysis | market | market | F02,F04 concepts |

## Integration seams
- Evidence service exposes approved evidence; other modules do not query its tables directly.
- Job analysis emits normalized requirements.
- Matching consumes requirements and approved evidence.
- Generation returns candidate text plus evidence provenance.
- Verification classifies candidates separately from user approval.
- Export consumes only approved, export-eligible statements.
