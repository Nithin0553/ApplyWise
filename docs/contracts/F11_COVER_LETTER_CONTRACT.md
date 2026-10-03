# F11 Cover Letter Contract

F11 drafts cover letter paragraphs from statements the user has already
approved, and keeps provenance all the way back to the original evidence. It
lives in `app/modules/generation/` beside F07 and reuses the same provider
seam.

## Identity and authorization

The route depends on F01's `require_role(UserRole.JOB_SEEKER)`. The user id is
taken from the authenticated session and never from the request body, so a
caller cannot draft a letter against another user's account by editing a
payload. `CoverLetterRequest` has no `user_id` field at all;
`CoverLetterService.generate` takes it as a keyword argument supplied by the
route.

Unauthenticated calls return 401, and a non-job-seeker role returns 403.

## Known gap: the approved-statement trust boundary

`approved_statements` currently arrives from the client. The `Literal` types on
`ApprovedStatement` prove the labels are well formed — an `UNSUPPORTED` or
unapproved statement cannot be represented by the model at all — but they do
**not** prove the statement ever passed F08 verification or F09 approval. A
caller can construct a new statement, set `verification_status="VERIFIED"` and
`approval_status="APPROVED"`, and send it. The guarantee is therefore
contractual, not enforced, in exactly the way F07's approved-evidence guarantee
is pending F02.

**Interim measure.** Because that is not safe to deploy, the endpoint is
prototype-only: `require_prototype_environment` returns 404 when
`APP_ENV=production`, so no production deployment can treat client-supplied
approval state as authoritative. The guard is specific to F11; F07's own route
is unaffected.

**How it closes.** `cover_letter_contracts` already holds the seam and the
selection logic:

- `ApprovedStatementProvider` is the interface F09 implements once statements
  are persisted — `list_approved_statements(user_id=...)`, returning only
  statements that are persisted, owned, verified and approved. It mirrors F02's
  `ApprovedEvidenceProvider`.
- `select_approved_statements(provider, user_id=..., statement_ids=...)` is what
  the route will call. The caller chooses *which* of its own approved statements
  to draw on; it supplies ids, never the statements or their approval state. An
  id that does not resolve to one of that user's approved statements raises
  `StatementNotApprovedError`, with one error for every reason — missing,
  foreign-owned, unverified, unapproved — so the response cannot be used to
  discover whether another user's statement exists.
- A partially valid selection is refused in full rather than trimmed: drafting
  from fewer statements than the user chose would misrepresent their request.

That logic is enforced and tested now, in
`apps/api/tests/test_cover_letter_trust_boundary.py`, including the forged,
foreign-owned and partially valid cases. Wiring it up when F09 lands is a change
of caller — `CoverLetterRequest` carries `statement_ids` instead of
`approved_statements`, and the guard comes off — not a change of policy.

## Where F11 sits in the chain

F07 generates candidate statements from approved **evidence**. F08 verifies
them, F09 is where the user approves them. F11 starts there: its input is
approved **statements**, not raw evidence.

```
evidence -> F07 -> candidate statements -> F08 -> F09 -> approved statements -> F11
```

## Input

`CoverLetterRequest` (`app.modules.generation.cover_letter_schemas`):

| Field | Meaning |
|---|---|
| `job_context` | Same `JobContext` type F07 uses. |
| `approved_statements` | One or more `ApprovedStatement`. IDs must be unique. |
| `tone` | `professional`, `warm` or `direct`. Default `professional`. |
| `max_paragraphs` | 2-5, default 3. |

`ApprovedStatement` carries `statement_id`, `text`, the `evidence_ids` behind
it, `verification_status` (`VERIFIED` or `INFERRED`) and `approval_status`
(`APPROVED`).

**Those last two fields are `Literal` types.** An `UNSUPPORTED` or unapproved
statement cannot be represented by the model at all, so it cannot enter a
cover letter even by accident. A request carrying one is rejected with HTTP
422 before any provider is called.

## Output

`CoverLetterDraft` carries run metadata, the accepted `paragraphs`, and
`rejected` entries with reasons.

`CoverLetterParagraph`:

| Field | Value |
|---|---|
| `paragraph_id` | Identifier for this draft paragraph. |
| `text` | 1-800 characters. |
| `statement_ids` | Which approved statements it draws on. Never empty. |
| `evidence_ids` | Union of those statements' evidence. Never empty. |
| `status` | Always `CANDIDATE`. |
| `verification_status` | Always `PENDING`. |
| `approval_status` | Always `UNREVIEWED`. |
| `export_eligible` | Always `False`. |

A paragraph is **new prose**, so it is a candidate in its own right: it goes
back through verification and approval before export, exactly as ADR-003
requires for edited content. Approving a statement does not approve a
paragraph written from it.

## Failure behavior

Identical to F07, and it reuses F07's error types:

| Situation | Result |
|---|---|
| Provider raises `AIProviderError` | `GenerationUnavailableError` (HTTP 503) |
| Provider raises anything else | `GenerationUnavailableError` (HTTP 503) |
| Response is not a `CoverLetterResponse` | `MalformedProviderResponseError` (HTTP 502) |
| A paragraph is malformed, empty, over-long, uncited, or cites an unknown statement | Dropped into `rejected`; the rest of the draft continues |

## Provider seam

`app/services/ai/provider.py` adds `CoverLetterRequest`, `RawParagraph`,
`CoverLetterResponse` and a `generate_cover_letter` method on `AIProvider`.
The stub and demo providers implement it. Providers see short references
(`S1`, `S2`) and never database identifiers, the same approach F07 uses for
evidence.

## Notes for F08 and F10 consumers

- Verify a paragraph against the statements in `statement_ids`, or against the
  evidence in `evidence_ids` — both are preserved.
- `rejected` entries are discarded provider text. Do not verify or store them.
- Export must treat an unapproved paragraph exactly as it treats an unapproved
  statement: it never reaches a document.

## Endpoint

`POST /api/generation/cover-letter/preview` (optional `?provider=stub|demo`).
Requires a bearer token for a Job Seeker; the draft is always owned by the
token's user. **Prototype-only**: returns 404 when `APP_ENV=production`, until
statement selection moves server-side (see the known gap above).

## Tests

`apps/api/tests/test_cover_letter_service.py` plus endpoint tests in
`apps/api/tests/test_generation_api.py`, with fixtures in
`apps/api/tests/fixtures/cover_letter_fixtures.py`, and trust-boundary tests in
`apps/api/tests/test_cover_letter_trust_boundary.py`. Between them they cover an
unauthenticated 401, a caller putting another user's id in the body, a forged
statement id, a foreign-owned statement, a partially valid selection, and the
production gate. All use a fake or bundled provider; no test performs a network
call.
