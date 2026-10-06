"""The F11 trust boundary: where approved statements must come from.

F11 drafts only from statements that F08 verified and F09 approved. Today the
client supplies those statements, and that is not good enough: the ``Literal``
types on ``ApprovedStatement`` prove the *labels* are well formed, not that the
statements ever passed verification or approval. A caller can construct a new
statement, set ``verification_status="VERIFIED"`` and ``approval_status=
"APPROVED"``, and send it.

This module is the seam that closes that gap. ``ApprovedStatementProvider`` is
the interface F09 implements once statements are persisted;
``select_approved_statements`` is the selection logic the route will call, and
it is already enforced and tested here. When persistence lands, the public
request carries ``statement_ids`` and the route resolves them through this
function — the same shape F07 uses for F02's
``ApprovedEvidenceProvider.list_grounding_contexts(...)``.

Keeping the logic here, rather than waiting for F09, means the rule is written
down and covered by tests now, and wiring it up later is a change of caller
rather than a change of policy.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from .cover_letter_schemas import ApprovedStatement
from .errors import GenerationError


class StatementNotApprovedError(GenerationError):
    """A requested statement is not an approved statement owned by this user.

    Deliberately one error for every reason — the statement does not exist, it
    belongs to someone else, it was never verified, it was never approved — so
    a caller cannot use the response to learn which. This mirrors how F02's
    evidence service refuses missing and foreign-owned records identically.
    """


class ApprovedStatementProvider(Protocol):
    """F09's seam: the approved statements a given user actually owns.

    F11 never queries statement storage itself, exactly as it never queries
    the evidence tables. The implementation is expected to return only
    statements that are persisted, owned by ``user_id``, verified by F08 and
    approved by the user in F09 — the same contract F02 offers for evidence.
    """

    def list_approved_statements(self, *, user_id: UUID) -> Sequence[ApprovedStatement]:
        """Return only approved statements owned by the requested user."""
        ...


def select_approved_statements(
    provider: ApprovedStatementProvider,
    *,
    user_id: UUID,
    statement_ids: Sequence[UUID],
) -> tuple[ApprovedStatement, ...]:
    """Resolve caller-supplied ids against what the user actually owns.

    The caller chooses *which* of their approved statements to draw on. It does
    not get to supply the statements themselves, or their approval state. Any
    id that does not resolve to one of this user's approved statements raises,
    rather than being quietly dropped: a letter drafted from fewer statements
    than the user selected would misrepresent what they asked for.

    Returns the statements in the order the caller listed them, so the S1/S2
    references in a draft follow the user's own ordering.
    """
    if not statement_ids:
        raise StatementNotApprovedError("No statements were selected.")

    owned = {
        statement.statement_id: statement
        for statement in provider.list_approved_statements(user_id=user_id)
    }

    selected: list[ApprovedStatement] = []
    seen: set[UUID] = set()
    for statement_id in statement_ids:
        if statement_id in seen:
            raise StatementNotApprovedError("Duplicate statement selected.")
        seen.add(statement_id)

        statement = owned.get(statement_id)
        if statement is None:
            raise StatementNotApprovedError(
                "One or more selected statements are not approved statements you own."
            )
        selected.append(statement)

    return tuple(selected)
