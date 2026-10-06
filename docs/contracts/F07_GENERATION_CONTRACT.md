# F07 Grounded Generation Contract

F07 turns approved career evidence plus job context into **candidate** resume
statements that carry provenance back to the evidence used. F07 owns
`app/modules/generation/` and the provider abstraction in `app/services/ai/`.

## Identity and authorization

The route depends on F01's `require_role(UserRole.JOB_SEEKER)`. The user id is
taken from the authenticated session and never from the request body, so a
caller cannot generate against another user's account by editing a payload.
`GenerationRequest` has no `user_id` field at all; `GenerationService.generate`
takes it as a keyword argument supplied by the route.

Unauthenticated calls return 401, and a non-job-seeker role returns 403.

## The approved-evidence trust boundary

The guarantee that generation draws only on approved evidence is **enforced**,
not merely contractual.

A caller selects evidence by **id**. It never supplies the records. The route
reads them for the authenticated user through F02's
`ApprovedEvidenceProvider.list_grounding_contexts(user_id=...)`, which returns
only evidence that is persisted, owned by that user, and APPROVED. There is no
field in which content or approval state could be sent, so neither can be
fabricated or altered in transit.

`resolution.resolve_approved_evidence(provider, user_id=..., evidence_ids=...)`
is where the rule lives:

- An id that does not resolve to one of this user's approved records raises
  `EvidenceNotApprovedError`, which the route returns as **404**.
- There is one error for every reason — the record does not exist, it belongs
  to another user, it was never approved — so a response cannot be used to
  discover whether someone else's evidence exists. F02's own service refuses
  missing and foreign-owned records identically, for the same reason.
- A partly valid selection is refused in full rather than trimmed. Generating
  from fewer items than the user chose would change what the statements rest
  on without anyone noticing.
- Records are returned in the order the caller listed them, so the E1/E2
  references in a result follow the user's own ordering.

The provider seam is restated structurally in `resolution.py` rather than
imported from F02, so the rule is testable with a fake store and no database.
The route supplies the real `EvidenceService`.

`apps/api/tests/test_generation_resolution.py` covers the rule directly;
`apps/api/tests/test_generation_api.py` drives real F02 records through the
HTTP route, including a fabricated id, another user's approved id, an
unapproved id, and a partly valid selection.

## Input

`GenerationPreviewRequest` (`app.modules.generation.schemas`) is the HTTP body:

| Field | Meaning |
|---|---|
| `job_context` | `JobContext`: job title, optional company, description, optional requirements. F04 supplies normalized requirements once available. |
| `evidence_ids` | One to twenty ids, unique, each an approved evidence record owned by the caller. |
| `max_statements` | 1-10, default 5. |

`GenerationRequest` is the **internal** model `GenerationService` consumes,
built by the route from the resolved records. It is not a shape any client can
send; keeping the two separate is what stops caller-supplied evidence reaching
the service. F07 still does not query the evidence tables itself — it reads
them through F02's documented seam and adapts them with
`app.modules.generation.adapters.from_grounding_context(s)`.

### Fields carried from F02

`GenerationEvidence` keeps the structured approved fields, not just title and
description: `evidence_type`, `title`, `organization`, `role`, `location`,
`description`, `skill_name`, `proficiency`, `credential`, `start_date`,
`end_date`. This matters for SKILL and CERTIFICATION evidence, whose meaning
lives in `skill_name` / `proficiency` / `credential` rather than in a
description that is often absent.

`source`, `source_url` and `approved_at` are deliberately **not** carried: they
are provenance metadata rather than content a provider should write from, and
provenance is tracked through `evidence_id`.

`to_prompt_text()` flattens an item to one labelled line
(`[skill] Python | skill: Python | proficiency: Advanced`), always placing the
free-text description last. `tests/test_generation_adapters.py` guards against
regressing to title-only grounding.

The adapter reads the F02 context structurally through a `Protocol` rather than
importing the evidence module, so F07 carries no build-time dependency on F02
and stays testable without a database.

## Output

`GenerationResult`:

| Field | Meaning |
|---|---|
| `generation_id`, `user_id`, `provider`, `generated_at` | Run metadata. |
| `statements` | Accepted `CandidateStatement` items. |
| `rejected` | Provider output F07 discarded, with a reason. Useful for QA and debugging; not for export. |

`CandidateStatement`:

| Field | Value |
|---|---|
| `statement_id` | Stable identifier for this candidate. |
| `text` | 1-500 characters. |
| `evidence_ids` | **Provenance.** At least one evidence ID. Never empty. |
| `status` | Always `CANDIDATE`. |
| `verification_status` | Always `PENDING`. F08 owns the real value. |
| `approval_status` | Always `UNREVIEWED`. F09 owns the real value. |
| `export_eligible` | Always `False`. |

These four fields are `Literal` types, so a candidate that claims to be
verified, approved, or export-eligible cannot be constructed at all.

## Hard rule

F07 output is never directly exportable. Verification (F08) and explicit user
approval (F09) remain separate mandatory steps. F07 performs neither.

## Notes for F08 consumers

- Read `statement.evidence_ids` to fetch the exact evidence a statement claims
  to rest on, then classify as `VERIFIED`, `INFERRED`, or `UNSUPPORTED`.
- `evidence_ids` is guaranteed non-empty, so an uncited statement never
  reaches verification: F07 rejects it first.
- A statement citing an evidence reference that was not supplied is rejected
  in full rather than partially trusted, so invented provenance never reaches
  F08.
- `rejected` entries are discarded provider text. Do not verify or store them
  as statements.
- Re-generation produces new `statement_id` values. Edited statements must be
  re-verified, per ADR-003.

## Provider seam

`app/services/ai/provider.py` defines `AIProvider`. Provider-specific code
lives only in `app/services/ai/`; feature modules never import a vendor SDK.

Providers receive short references (`E1`, `E2`) instead of database UUIDs:
language models repeat short tokens more reliably, and any reference the
provider invents is detected and rejected during mapping back to real IDs.

`AI_PROVIDER=stub` selects the deterministic offline `StubAIProvider`
(`app/services/ai/stub.py`) used for local development and tests.

## Failure behavior

| Situation | Result |
|---|---|
| Provider raises `AIProviderError` | `GenerationUnavailableError` |
| Provider raises anything else (timeout, SDK bug) | `GenerationUnavailableError` |
| Response is not a `GroundedGenerationResponse` | `MalformedProviderResponseError` |
| A single statement is malformed, empty, over-long, uncited, or cites an unknown reference | Statement dropped into `rejected`; the rest of the run continues |
| A selected evidence id is unknown, unapproved, or owned by another user | `EvidenceNotApprovedError`, returned as HTTP 404 before any provider call |

All three errors subclass `GenerationError`.

## Tests

| Test file | Covers |
|---|---|
| `tests/test_generation_service.py` | Grounding, rejection and failure paths |
| `tests/test_ai_provider.py` | The bundled stub and demo providers |
| `tests/test_generation_adapters.py` | F02 structured fields surviving into the prompt |
| `tests/test_generation_resolution.py` | The trust boundary, against a fake store |
| `tests/test_generation_api.py` | The HTTP route end to end, through real F01 and F02 |
| `apps/web/src/features/tailoring/evidenceMapping.test.ts` | The browser's view of an F02 record |

All tests use a fake or bundled provider and an in-memory database; no test
performs a network call or needs an API key.
