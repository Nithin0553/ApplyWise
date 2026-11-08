# F15 Interview Defensibility Contract

F15 helps a user rehearse for an interview about the claims on their own
resume. For each approved statement it returns the questions an interviewer is
likely to ask, the material from the user's own evidence they can answer with,
and a warning when a claim asserts something the evidence does not contain.

It lives in `app/modules/generation/` per `docs/FEATURE_BOUNDARIES.md`, beside
F07 and F11, and reuses their seams. The frontend home is
`apps/web/src/features/interview/`.

## Defensibility is not verification

This is the most important line in the contract.

F08 owns verification. It decides whether a claim is `VERIFIED`, `INFERRED` or
`UNSUPPORTED` against the user's evidence, and that decision gates export under
ADR-003. F09 owns approval.

F15 decides something narrower and softer: **how hard a claim would be to
explain out loud if an interviewer pressed on it.** A `HARD_TO_DEFEND` result
means "your evidence does not answer the obvious follow-up question", which is
advice to the user. It is not a verification outcome, it does not gate
anything, and it must never be displayed or stored as though it were.

Three things enforce that separation:

- `InterviewPrep` carries `advisory_only: Literal[True]`.
- No model in `interview_schemas` has an approval, verification or export
  field. There is nothing on the response that F08 or F09 could be mistaken
  for, and nothing a caller could coerce into one.
- `DefensibilityRisk` deliberately uses different words from F08's vocabulary
  (`SUPPORTED` / `NEEDS_DETAIL` / `HARD_TO_DEFEND`, never `UNSUPPORTED`).

## Identity and authorization

The route depends on F01's `require_role(UserRole.JOB_SEEKER)`. The user id
comes from the authenticated session and never from the request body:
`InterviewPrepRequest` has no `user_id` field, and
`InterviewPreparationService.prepare` takes it as a keyword argument supplied
by the route.

Unauthenticated calls return 401; a non-job-seeker role returns 403.

## Trust boundary: half enforced today

F15 compares a claim against the evidence behind it, so the integrity of the
**evidence** side is what makes the check meaningful. That side is enforced.

- The route collects every evidence id cited by every submitted statement and
  resolves them through `resolution.resolve_approved_evidence`, which returns
  only records that are persisted, owned by the authenticated user, and
  APPROVED.
- An id that does not resolve raises, and the route answers **404** — the same
  response for a missing id, a foreign-owned id and an unapproved id, so the
  reply cannot be used to learn which.
- A caller therefore cannot supply flattering evidence that appears to justify
  any claim at all. If it could, the feature would be worthless.

The **statement** side is not enforced yet, for the same reason as F11: F09
has no store to resolve statement ids against, so `approved_statements` still
arrives from the client. A caller could submit statement text the user never
approved.

**Interim measure.** The route reuses F11's `require_prototype_environment`
dependency and returns 404 when `APP_ENV=production`, so no production
deployment can treat client-supplied approval state as authoritative.

**How it closes.** `cover_letter_contracts` already holds the seam and the
selection logic, written and tested:

- `ApprovedStatementProvider.list_approved_statements(user_id=...)` is the
  interface F09 implements once statements are persisted.
- `select_approved_statements(provider, user_id=..., statement_ids=...)`
  resolves caller-supplied ids against what the user owns and raises
  `StatementNotApprovedError` identically for every failure reason.

When F09 lands, `InterviewPrepRequest.approved_statements` becomes
`statement_ids`, the route calls `select_approved_statements`, and the
production gate comes off. That is a change of caller, not a change of policy.

Note for whoever wires F09: do **not** resolve statements from F13's reviewed
drafts. Those carry `ProvenanceOrigin.DRAFT_USER_REVIEWED` precisely because
no server-side verification stands behind them. F15 should read only
statements marked `F09_APPROVED`.

## Why the check is deterministic

F07 and F11 ask a language model for prose and then distrust what comes back.
F15 asks nothing of a model at all. Every signal is a textual comparison
between an approved statement and the evidence it cites.

That buys four things:

- The same inputs always produce the same advice, so the result is testable.
- Each warning can be explained to the user line by line — it names the word
  or figure that triggered it.
- The feature works today, with no F08, no F09 and no provider.
- There is no second hallucination surface. A feature whose job is to catch
  unsupported claims should not be able to invent one.

Provider-written questions remain possible later, behind the same validation
the other two features use, but the defensibility judgement itself should stay
deterministic.

## Signals

| Code | Raised when | Severity |
|---|---|---|
| `UNSOURCED_NUMBER` | The statement contains a quantity (`40%`, `$2M`, `1,200`) that appears in no cited evidence | serious |
| `UNSOURCED_SUPERLATIVE` | The statement claims rank or uniqueness (`first`, `only`, `best`, …) that the evidence does not state | serious |
| `UNSOURCED_LEADERSHIP` | The statement claims scope over others (`led`, `managed`, `owned`, …) and no cited evidence records a role or organization | serious |
| `THIN_EVIDENCE` | The cited evidence carries fewer than 80 characters of description in total | warning |
| `INFERRED_STATEMENT` | The statement's F08 status is `INFERRED` rather than `VERIFIED` | warning |
| `SINGLE_SOURCE` | The statement rests on exactly one evidence item | warning |

Any serious signal yields `HARD_TO_DEFEND`. Warnings alone yield
`NEEDS_DETAIL`. No signals yields `SUPPORTED`.

Quantities are compared against the raw evidence text, not a normalized copy,
so `1,200` in the evidence matches `1,200` in the statement rather than
splitting into two tokens and reporting a sourced figure as unsourced.

The heuristics are word-level and will not catch paraphrase: a statement
claiming "nearly half" against evidence recording "40%" raises nothing. That
is a deliberate bias toward silence over false accusation — the cost of a
missed warning is a harder interview, while the cost of a false one is a user
deleting a true claim from their resume.

## Input

```json
{
  "approved_statements": [
    {
      "statement_id": "…",
      "text": "Reduced regression runtime by 85%",
      "evidence_ids": ["…"],
      "verification_status": "VERIFIED"
    }
  ]
}
```

Bounds: at most 20 statements per request, at most 50 distinct cited evidence
items across the whole request, statement ids unique. The evidence bound is
separate from the statement bound because one statement may cite many items,
so a request well inside the statement limit could otherwise ask the route to
read an unbounded number of records from F02.

## Output

`InterviewPrep` with one `StatementPreparation` per submitted statement, in the
order the caller listed them. Each carries:

- `risk` and the `signals` that produced it, each naming what triggered it.
- `questions` — baseline questions first so a fully supported statement still
  has something to rehearse, then one question per distinct signal. Bounded at
  six per statement.
- `supporting_points` — the cited evidence restated as talking points. These
  are assembled from fields the user already approved and are never generated
  prose, so rehearsing an answer cannot drift into inventing one.

## Failure behavior

| Condition | Response |
|---|---|
| Not authenticated | 401 |
| Wrong role | 403 |
| Any cited evidence id missing, foreign-owned or unapproved | 404, identical body in all three cases |
| Duplicate statement ids, empty request, bounds exceeded | 422 |
| `APP_ENV=production` | 404 |

`MissingEvidenceForStatementError` exists for the case where the service is
handed a statement citing evidence the caller did not resolve. The route
resolves every cited id first, so it indicates a programming error rather than
anything a user can trigger. It raises rather than analysing a claim against
part of its evidence, which would report confident nonsense.

## Endpoint

`POST /api/interview/preparation`

The router is mounted in `app/main.py`. `test_the_preparation_route_is_mounted`
asserts the path appears in `openapi.json`, because F04's analysis router
shipped unmounted while its own unit tests passed and every call returned 404.

## Tests

- `tests/test_interview_service.py` — signal classification, the
  sourced-figure and backed-leadership negative cases, question bounds,
  ordering, and the advisory-only guarantee.
- `tests/test_interview_api.py` — the mounted route, authentication,
  ownership, indistinguishable 404s, the advisory response shape, and the
  production gate.
- `tests/fixtures/interview_fixtures.py` — statements shaped to trip exactly
  one signal each, standing in for F09 output.
