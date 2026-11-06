"""Deterministic fixtures for F15 tests.

The statements here stand in for F09 output, which has no store yet. Each one
is shaped to exercise exactly one defensibility signal, so a failing test
names the rule that broke.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.modules.generation.cover_letter_schemas import ApprovedStatement
from app.modules.generation.schemas import GenerationEvidence

USER_ID = UUID("00000000-0000-0000-0000-0000000000aa")
WORK_EVIDENCE_ID = UUID("11111111-1111-1111-1111-111111111111")
SKILL_EVIDENCE_ID = UUID("22222222-2222-2222-2222-222222222222")
MEASURED_EVIDENCE_ID = UUID("33333333-3333-3333-3333-333333333333")

# Rich evidence: a role, an organization, dates and a long description.
WORK_EVIDENCE = GenerationEvidence(
    evidence_id=WORK_EVIDENCE_ID,
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

# Thin evidence: no description, no role, no organization.
SKILL_EVIDENCE = GenerationEvidence(
    evidence_id=SKILL_EVIDENCE_ID,
    evidence_type="skill",
    title="Python",
    skill_name="Python",
    proficiency="Advanced",
)

# Evidence that records a figure, so a statement may legitimately quote it.
MEASURED_EVIDENCE = GenerationEvidence(
    evidence_id=MEASURED_EVIDENCE_ID,
    evidence_type="project",
    title="Regression suite rework",
    organization="Model N",
    role="QA Engineer",
    description=(
        "Reworked the nightly regression suite and cut its runtime by 40% while "
        "keeping coverage of the billing paths unchanged."
    ),
)

EVIDENCE_BY_ID = {
    WORK_EVIDENCE_ID: WORK_EVIDENCE,
    SKILL_EVIDENCE_ID: SKILL_EVIDENCE,
    MEASURED_EVIDENCE_ID: MEASURED_EVIDENCE,
}


def statement(
    suffix: int,
    text: str,
    evidence_ids: tuple[UUID, ...],
    verification_status: str = "VERIFIED",
) -> ApprovedStatement:
    return ApprovedStatement(
        statement_id=UUID(f"aaaaaaaa-0000-0000-0000-{suffix:012d}"),
        text=text,
        evidence_ids=evidence_ids,
        verification_status=verification_status,  # type: ignore[arg-type]
    )


WELL_SUPPORTED = statement(
    1,
    "Built and maintained automated regression suites for revenue management software",
    (WORK_EVIDENCE_ID, MEASURED_EVIDENCE_ID),
)

UNSOURCED_FIGURE = statement(
    2,
    "Reduced regression runtime by 85% across the release trains",
    (WORK_EVIDENCE_ID, MEASURED_EVIDENCE_ID),
)

SOURCED_FIGURE = statement(
    3,
    "Cut nightly regression runtime by 40% without losing billing coverage",
    (WORK_EVIDENCE_ID, MEASURED_EVIDENCE_ID),
)

UNSOURCED_LEADERSHIP = statement(
    4,
    "Led the automation effort for the platform",
    (SKILL_EVIDENCE_ID,),
)

UNSOURCED_SUPERLATIVE = statement(
    5,
    "Delivered the first automated regression suite the team had",
    (WORK_EVIDENCE_ID, MEASURED_EVIDENCE_ID),
)

INFERRED_THIN = statement(
    6,
    "Comfortable writing production Python",
    (SKILL_EVIDENCE_ID,),
    verification_status="INFERRED",
)
