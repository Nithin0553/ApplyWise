"""Deterministic fixtures for F08 tests.

``FakeEvidence`` mirrors F02's ``EvidenceGroundingContext`` structurally, which
is all F08 reads, so the classifier can be tested without a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

USER_ID = UUID("00000000-0000-0000-0000-0000000000aa")
WORK_ID = UUID("11111111-1111-1111-1111-111111111111")
SKILL_ID = UUID("22222222-2222-2222-2222-222222222222")
MEASURED_ID = UUID("33333333-3333-3333-3333-333333333333")

APPROVED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class FakeEvidence:
    """The attributes F08 reads from an approved F02 record."""

    evidence_id: UUID
    evidence_type: str
    title: str
    organization: str | None = None
    role: str | None = None
    location: str | None = None
    description: str | None = None
    skill_name: str | None = None
    proficiency: str | None = None
    credential: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    approved_at: datetime = APPROVED_AT


WORK = FakeEvidence(
    evidence_id=WORK_ID,
    evidence_type="work_experience",
    title="Associate QA Engineer",
    organization="Model N",
    role="Associate QA Engineer",
    description=(
        "Built and maintained automated regression suites for revenue management "
        "software across two release trains."
    ),
    start_date=date(2022, 7, 1),
    end_date=date(2024, 11, 30),
)

SKILL = FakeEvidence(
    evidence_id=SKILL_ID,
    evidence_type="skill",
    title="Python",
    skill_name="Python",
    proficiency="Advanced",
)

MEASURED = FakeEvidence(
    evidence_id=MEASURED_ID,
    evidence_type="project",
    title="Regression suite rework",
    organization="Model N",
    role="QA Engineer",
    description=(
        "Reworked the nightly regression suite and cut its runtime by 40% while "
        "keeping coverage of the billing paths unchanged."
    ),
)

APPROVED = {WORK_ID: WORK, SKILL_ID: SKILL, MEASURED_ID: MEASURED}


class FakeEvidenceProvider:
    """Stands in for F02's ``list_grounding_contexts`` seam."""

    def __init__(self, items: tuple[FakeEvidence, ...] = ()) -> None:
        self.items = items

    def list_grounding_contexts(self, *, user_id: UUID):  # noqa: ANN201
        del user_id
        return self.items
