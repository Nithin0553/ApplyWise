# ApplyWise production release preflight

**Status:** Not executed. This is a procedure, **not** deployment approval or evidence of manual STD execution.
**Scope:** F01 hardening PR #57 and the merged F08→F09→F13→F10 workflow. **Owner:** authorized ApplyWise Railway operator plus PM/reviewer.

## Current baseline (checked 2026-11-10)

- Railway's production web, API, and Postgres services are online; the active web/API deployments were created on **2026-11-06**. A successful GitHub merge does not mean those builds are live.
- The Railway OAuth connection can see that the API has `APP_ENV` and `APP_SECRET_KEY` **names**, but cannot read their **values**. These existing variables must not be overwritten, echoed, pasted into GitHub, or treated as proof of strength.
- F01 #57 rejects the committed default or keys shorter than 32 **UTF-8 bytes** in `APP_ENV=production`, and normalizes capitalization so prototype-only routes and OpenAPI docs use the same environment policy.
- F08 verification, F09 review, F13 trusted finalization and F10 PDF/DOCX export plus real-provider API tests are merged on `main`. This says nothing yet about Railway runtime behavior.

## Gate 1 — confidential security verification (must be done by a Railway operator)

Verify the production **API service**'s current `APP_ENV` and `APP_SECRET_KEY` within an authorized Railway shell/session. **Never send the key or its length to chat, logs, comments, screenshots, or a test report.** This read-only snippet prints just one status:

```bash
python - <<'PY'
import os
import sys

default = "replace-me-locally-with-a-random-32-byte-secret"
environment = os.environ.get("APP_ENV", "").strip().lower()
secret = os.environ.get("APP_SECRET_KEY", "")
ready = (
    environment == "production"
    and secret != default
    and len(secret.encode("utf-8")) >= 32
)
print("F01 production-environment preflight:", "PASS" if ready else "BLOCKED")
sys.exit(0 if ready else 1)
PY
```

A PASS confirms only the specified settings and minimum length. The operator must **also attest privately** that the key was generated with a cryptographically secure random generator, is unique to this environment, is not shared in source/config/docs, and is managed in Railway. If any check fails, **block deployment**, generate/set a strong secret in the authorized variable manager, and coordinate token/session invalidation with the team. Do not set `APP_ENV=development` as a workaround.

Record only operator, timestamp, deployment target and PASS/BLOCKED outcome in the release issue. Do **not** provide any secret details.

## Gate 2 — release preparation and backup

1. Confirm PR #57 is merged only after Gate 1. Check CI and Security Baseline on the exact head and confirm all required code reviews.
2. Take and verify a recoverable production Postgres backup/snapshot **before** applying migrations. Record a private recovery reference, not credentials or data.
3. Confirm the linear Alembic migration head and review pending migrations; the API start command runs `python -m alembic upgrade head` **before** the server starts. A schema change may not be safely reverted merely by redeploying an older container.
4. Record the exact `main` commit and intended web/API artifacts. Stage/test on a separate environment or disposable database where available.
5. Plan a short maintenance window and designate an operator to watch application, database and auth errors during the release.

## Gate 3 — controlled deployment and smoke tests

Deploy the reviewed commit deliberately through the project's existing Railway services; do **not** create duplicate services. Verify new deployment IDs and that health checks reach healthy status.

Using **synthetic accounts and evidence only**, collect redacted results for:
- API `/health` is healthy; production `/docs` and the F11/F15 prototype-only routes are not available.
- New login/register tokens work and unauthorized/foreign-owner requests remain denied.
- F02 approved evidence → real F08 verdict → F09 current-revision approval → F13 trusted finalization → F10 PDF **and** DOCX render successfully and contain the approved claim text.
- UNSUPPORTED claims cannot be approved or exported; an INFERRED claim must require explicit F09 approval and remain labeled INFERRED.
- Editing/unconfirming cited evidence invalidates current approval and makes previously saved F13 versions return a non-exportable response **before rendering**.
- Check log/error rates and the production web application's relevant navigation and responsive behavior after deployment.

If any critical gate fails, stop rollout and triage. A service rollback does not automatically reverse migrated data; follow the database recovery plan before attempting an older application build.

## Gate 4 — professor STD execution and sign-off

The automated integration test PR #71 exercises a synthetic test client (376 backend / 115 frontend tests at last check), **not** a manually executed STD case. Keep all unexecuted result cells as **N/A**, not Pass. For each selected submission test, record actual observed responses, reproducible test data, exact build/deployment, system/browser versions, timestamps, defects, evidence and human reviewer sign-off. Use `docs/testing/STD_SUBMISSION_CASE_MAP.md` for the reduced eight-case numbering (original TC-11 → submitted TC-6).

**Release completion requires a passed security preflight, reviewed/healthy deployment, real smoke evidence and signed manual STD results.** No checkbox or written declaration substitutes for those observed actions.
