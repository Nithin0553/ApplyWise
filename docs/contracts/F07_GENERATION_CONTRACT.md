# F07 Grounded Generation Contract

F07 turns approved career evidence plus job context into **candidate** resume
statements that carry provenance back to the evidence used. F07 owns
`app/modules/generation/` and the provider abstraction in `app/services/ai/`.

## Input

`GenerationRequest` (`app.modules.generation.schemas`):

| Field | Meaning |
|---|---|
| `user_id` | Owner of the evidence. Generation never mixes users. |
| `job_context` | `JobContext`: job title, optional company, description, optional requirements. F04 supplies normalized requirements once available. |
| `approved_evidence` | One or more `GenerationEvidence` items. Evidence IDs must be unique. |
| `max_statements` | 1-10, default 5. |

Callers must build `GenerationEvidence` from F02's
`ApprovedEvidenceProvider.list_grounding_contexts(user_id=...)` using
`app.modules.generation.adapters.from_grounding_context(s)`. F07 does not query
the evidence tables and cannot itself confirm approval state; supplying
unapproved evidence violates this contract.

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

Both errors subclass `GenerationError`.

## Tests

`apps/api/tests/test_generation_service.py` and
`apps/api/tests/test_ai_provider.py`, with deterministic fixtures in
`apps/api/tests/fixtures/generation_fixtures.py`. All tests use a fake or stub
provider; no test performs a network call.
