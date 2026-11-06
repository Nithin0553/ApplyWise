# ApplyWise UI — approved baseline and integration map

**Baseline:** 19-screen ApplyWise storyboard, finalized November 2026.  
**Entry point:** `apps/web/src/App.tsx` → `GuidedJourney`.  
**Design source:** `ApplyWise_All_Page_Designs.zip` (user-approved reference).  
**Deployment:** Railway, `apps/web` as the public web service and `apps/api` as a private FastAPI service with PostgreSQL.  
**Important:** This release does **not** include Demo Mode.

## Approved appearance and flow

- White surfaces, blue/green gradients, animated brand introduction and inline light sweep.
- Existing authentication (sign in/register) with an aligned design.
- Sequential six-step profile onboarding, collapsible/stacked answers, optional resume selection.
- Preparation animation → success state → job description entry.
- Two distinct stages: extracted job details; evidence/keyword-overlap matching.
- Resume generation state, document-like preview, expandable candidate statements, user approval or denial.
- Reviewed-text download, saved application/resume version, Applications dashboard.
- Responsive mobile/laptop layouts and reduced-motion support.

## Verified integration surfaces

| UI action | Backend integration | Handling |
| --- | --- | --- |
| Login/register/session | `/auth/login`, `/auth/register`, `/auth/me` | F01 JWT session. |
| Onboarding answers | Browser storage keyed by account ID | No claim of server-side profile persistence. |
| Submitted experience | `POST /api/evidence/` | F02 stores it as **unconfirmed** evidence. |
| Evidence list and approval | `GET /api/evidence/`, `POST /api/evidence/{id}/approve` | Only approved evidence is used for grounding. |
| Job text/requirements | Client-side transparent rule-based extraction | **Not** a verified external posting or a finished F04 analyzer. |
| Evidence match percentage | Client-side word overlap against approved evidence | **Not** an ATS/hiring score. |
| Draft resume statements | `POST /api/generation/preview?provider=demo` | F07 grounded, scripted provider. Statements remain candidates. |
| Claim review | UI-held approve/deny decisions | Human-reviewed, **not** automated F08 verification. |
| Save application and resume version | `POST /api/applications/`; `POST /api/applications/{id}/resume-versions` | F13 stores the version with provenance, `INFERRED` status. |
| Applications dashboard | `GET /api/applications/` and per-application version listing | Uses saved records, not mock counts. |
| Download | Client-side plain-text export | Reviewed `.txt`; not final DOCX/PDF. |

## Deferred integrations

These are genuine backend work items, **not** cosmetic changes and not implied by the current UI:

1. PDF/DOCX/TXT resume ingestion: selecting a file currently stores its name locally; no file contents are uploaded or parsed.
2. Fully integrated job-description analysis (F04), semantic match calculation (F05), and an actual configurable AI provider instead of F07's demo adapter.
3. Server-verified claim status and durable approval/rejection persistence (F08/F09).
4. Professionally formatted PDF/DOCX export (F10), with server-enforced eligibility.
5. Any other earlier prototype modules (e.g. cover letter, sharing) need product-flow decisions and production endpoint verification before being surfaced as completed actions.

## Maintenance rules

- **This is the final design baseline.** Future requested minor changes should be small feature branches and PRs, not a second incompatible UI shell.
- Never turn placeholder illustrations or hardcoded percentages from the storyboard into production user data.
- Never describe human approval as automated verification.
- Keep all changes in reviewed PRs with frontend tests/build, backend tests and security checks.
- Do not introduce Demo Mode. Preserve real sign-in and account isolation.
- The Railway web service must proxy both `/auth/*` and `/api/*` to the private API; production is built with `VITE_API_BASE_URL` empty so auth uses the same origin.
- Deploy the same reviewed repository branch as the source of truth, then verify the web and API health statuses.
