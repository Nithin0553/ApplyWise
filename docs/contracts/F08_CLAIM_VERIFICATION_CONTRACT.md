# F08 Claim Verification Contract

**Owner:** @niraalibandi (issue #6). **Consumers:** F09 statement review (@Nithin0553, #58), then F13 trusted finalization (#22) and F10 export.
**SRS traceability:** Req-Func-Sw-37 – Req-Func-Sw-42 (F08), supporting Req-Qual-Trace-1 and Req-Qual-Trace-2. Approved SRS version 3.0, 09/25/2026, Appendix A.

F08 decides, independently of the user, what the user's own approved evidence
actually supports. It classifies each claim `VERIFIED`, `INFERRED` or
`UNSUPPORTED`, and says why.

Backend home `apps/api/app/modules/verification/`; frontend home
`apps/web/src/features/verification/`, per `docs/FEATURE_BOUNDARIES.md`.

## Verification is not approval

F08 says what the evidence supports. F09 is where the user decides to stand
behind a claim. The two are deliberately separate, and neither substitutes for
the other: a `VERIFIED` claim the user never approved is not exportable, and an
approval recorded against a claim F08 no longer certifies is invalidated.

F08 therefore has no approval concept, no approval field, and no endpoint that
can approve anything.

## What a caller may and may not send

A caller submits a claim and the ids of the approved evidence it cites. That is
all.

`StatementSubmission` carries `text` and `evidence_ids`, is declared
`extra="forbid"`, and has no `status` or `revision` field. A request that tries
to assert its own verdict is a 422, not a silent ignore — there is a test for
exactly that.

The *text* is the user's own and F08 does not police what a person may write
down; the point of the feature is to judge it. What a caller cannot do is
decide what the claim is worth. The evidence is resolved server-side from F02
for the authenticated user, so a claim is always judged against material the
user genuinely owns and has approved. A cited id that is missing, unapproved,
or owned by someone else resolves to nothing and the claim is `UNSUPPORTED`.

## The classes, and why the lines are drawn there

| Class | Meaning | Export |
|---|---|---|
| `VERIFIED` | No fabricated specifics, and the claim's own content words substantially appear in the cited evidence | Allowed |
| `INFERRED` | Grounded — nothing invented — but the wording goes beyond what the evidence literally records | Allowed |
| `UNSUPPORTED` | The claim states a specific the evidence does not contain, or its evidence is gone | **Blocked** (Req-Qual-Trace-2) |

`UNSUPPORTED` is reserved for **fabricated specifics that can be checked
objectively**: a figure or a ranking absent from the evidence. These block
export, so a false positive costs a user a true claim on their resume. That is
the expensive mistake, and the bar is set to avoid it.

Claims of scope — "led", "owned", "managed" — without a role recorded in the
evidence are `INFERRED`, not `UNSUPPORTED`. Scope language is interpretive and
the user may well be right. This is also where F08 and F15 deliberately differ:
F15 flags the same wording as hard to defend in an interview, which is advice,
while F08 declines to block it from export, which is a gate. Different jobs,
the same philosophy.

## Findings

Every classification carries `findings`, each naming the figure or word that
triggered it: `FIGURE_NOT_IN_EVIDENCE`, `RANKING_NOT_IN_EVIDENCE`,
`SCOPE_NOT_IN_EVIDENCE`, `EVIDENCE_NOT_AVAILABLE`, `BEYOND_EVIDENCE_WORDING`,
`FULLY_COVERED`.

A verdict without a reason is not actionable. A user told "unsupported" with no
explanation can only guess, and guessing here means deleting claims that were
true.

## Why it is deterministic

F07 asks a language model for prose and distrusts what comes back. F08 asks
nothing of a model at all: every decision is a textual comparison between a
claim and its evidence.

That buys reproducibility, an explanation the user can read, availability with
no provider configured — and, most importantly, it means the component that
decides whether a claim is supported cannot itself hallucinate.

The matching is lexical, not semantic. "nearly half" against evidence recording
"40%" raises nothing. That is a deliberate bias toward silence over false
accusation, and it is the main known limitation.

## The revision — the guarantee everything else rests on

F09 invalidates an approval when the revision moves. F13 refuses to export a
snapshot whose revision is no longer current. Both are hollow if a claim's
meaning can change while its revision stays put.

So the revision is **derived, not stored**. It is a SHA-256 over the claim text,
the cited evidence ids, the current content *and approval timestamp* of each
cited record, and the resulting classification, rendered as `v1-` plus 32 hex
characters — within the 8–128 character, `^[a-zA-Z0-9._:-]+$` bounds F09
validates.

Rotation is therefore structural. There is no code path that changes what a
claim says, or what backs it, and leaves the revision untouched, because the
revision is a function of exactly those things. A guarantee that depended on
remembering to increment a counter would not be a guarantee.

Consequences, each covered by a test:

- Editing the claim rotates it.
- Editing any cited evidence record rotates it.
- Re-approving evidence rotates it, even when the words are identical — which
  is what F13's "reapproval of identical text on a new revision" test needs.
- Unapproving or deleting evidence rotates it, via reclassification.
- Changing the cited set rotates it.
- Reordering citations does **not** rotate it: order is presentation, not
  substance, and must not look like an edit.

## Nothing is cached

Classification and revision are not columns. Only the claim and its cited ids
are stored; both verdict and revision are recomputed on every read.

That is what makes `list_current` authoritative rather than a snapshot: editing
evidence changes the answer immediately, with no job to run and no cache to
invalidate. The cost is one F02 read per call instead of per statement.

## The F09 seam

`VerificationProvider` in `contracts.py` is the shape F09 consumes:

```python
get_current(*, user_id: UUID, statement_id: UUID) -> VerifiedStatement | None
list_current(*, user_id: UUID) -> tuple[VerifiedStatement, ...]
```

`get_current` returns `None` identically for a statement that does not exist
and one owned by somebody else. `list_current` returns statements whose
evidence has gone as `UNSUPPORTED` rather than omitting them — F09 needs to see
that an approval has been invalidated, and a silently missing statement looks
the same as one that never existed.

The protocol is **restated structurally** rather than imported from
`app.modules.statement_review`, exactly as F07's `resolution` restates F02's
provider. Neither module depends on the other at build time, and
`tests/test_verification_f09_compatibility.py` proves the shapes still match —
field names, keyword-only signatures, StrEnum value equality across the two
modules, and the revision format F09 validates.

**Wiring, once F09 merges:** override F09's `current_verification_provider`
dependency to return `VerificationService(db, EvidenceService(db))`. That is a
change of caller, not of policy.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/verification/statements` | Submit a claim; returns the verdict |
| GET | `/api/verification/statements` | All held claims, re-classified now |
| GET | `/api/verification/statements/{id}` | One claim, re-classified now |
| DELETE | `/api/verification/statements/{id}` | Withdraw a claim |

All require F01 job-seeker access. Unauthenticated 401, wrong role 403, missing
or foreign id 404 with an identical body, bounds violations 422, more than 200
held statements 409.

Unlike F11 and F15 this needs no production gate: nothing a client sends can
assert a verification outcome.

`test_the_verification_routes_are_mounted` asserts the path appears in
`openapi.json`, because F04's router shipped unmounted while its own unit tests
passed and every call returned 404.

## Tests

- `tests/test_verification_analysis.py` — the adversarial corpus. Fabricated
  figures and rankings in both directions, including the cases that must **not**
  be flagged, plus every revision-rotation property above.
- `tests/test_verification_api.py` — mounted routes, ownership, indistinguishable
  404s, forged-verdict rejection, and the end-to-end invalidation case where
  unapproving evidence flips a `VERIFIED` claim to `UNSUPPORTED` and moves its
  revision.
- `tests/test_verification_f09_compatibility.py` — structural compatibility with
  F09's declared provider.

## Known limitations

- Lexical matching only; paraphrase is not detected.
- Date and duration claims are not checked against evidence date ranges.
- `VERIFIED` uses a 60% content-word coverage threshold, which is a judgement
  call rather than a measured one. It should be re-tuned against a labelled
  sample before anyone claims the 90% accuracy figure in Req-Qual-Match-3.
