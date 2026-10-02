# F11 Cover Letter Contract

F11 drafts cover letter paragraphs from statements the user has already
approved, and keeps provenance all the way back to the original evidence. It
lives in `app/modules/generation/` beside F07 and reuses the same provider
seam.

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
| `user_id` | Owner of the statements. |
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
Local development only; it carries no authentication, because F01 owns that.

## Tests

`apps/api/tests/test_cover_letter_service.py` (22) plus endpoint tests in
`apps/api/tests/test_generation_api.py`, with fixtures in
`apps/api/tests/fixtures/cover_letter_fixtures.py`. All use a fake or bundled
provider; no test performs a network call.
