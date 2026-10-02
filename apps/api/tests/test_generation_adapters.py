"""F02 -> F07 adapter: structured approved fields must survive into the prompt.

Regression guard for the integration note on PR #8: an adapter that kept only
title/organization/role/description would silently drop the meaning of SKILL
and CERTIFICATION evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from app.modules.generation.adapters import from_grounding_context, from_grounding_contexts
from app.modules.generation.schemas import GenerationRequest, JobContext
from app.modules.generation.service import GenerationService
from tests.fixtures.generation_fixtures import FakeAIProvider, response_with


@dataclass(frozen=True)
class FakeGroundingContext:
    """Mirrors F02's EvidenceGroundingContext without importing the module."""

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


SKILL_CONTEXT = FakeGroundingContext(
    evidence_id=uuid4(),
    evidence_type="skill",
    title="Python",
    skill_name="Python",
    proficiency="Advanced",
)

CERTIFICATION_CONTEXT = FakeGroundingContext(
    evidence_id=uuid4(),
    evidence_type="certification",
    title="ISTQB Foundation Level",
    organization="ISTQB",
    credential="CTFL-2023-44810",
    start_date=date(2023, 5, 1),
)

WORK_CONTEXT = FakeGroundingContext(
    evidence_id=uuid4(),
    evidence_type="work_experience",
    title="Associate QA Engineer",
    organization="Model N",
    role="Associate QA Engineer",
    location="Hyderabad",
    description="Built automated regression suites.",
    start_date=date(2022, 6, 1),
    end_date=date(2024, 12, 31),
)


def test_skill_fields_survive_the_adapter() -> None:
    evidence = from_grounding_context(SKILL_CONTEXT)

    assert evidence.skill_name == "Python"
    assert evidence.proficiency == "Advanced"
    assert evidence.evidence_type == "skill"


def test_certification_fields_survive_the_adapter() -> None:
    evidence = from_grounding_context(CERTIFICATION_CONTEXT)

    assert evidence.credential == "CTFL-2023-44810"
    assert evidence.organization == "ISTQB"
    assert evidence.start_date == date(2023, 5, 1)


def test_prompt_text_carries_structured_fields_not_just_the_title() -> None:
    skill_text = from_grounding_context(SKILL_CONTEXT).to_prompt_text()
    certification_text = from_grounding_context(CERTIFICATION_CONTEXT).to_prompt_text()
    work_text = from_grounding_context(WORK_CONTEXT).to_prompt_text()

    assert "skill: Python" in skill_text
    assert "proficiency: Advanced" in skill_text
    assert "credential: CTFL-2023-44810" in certification_text
    assert "location: Hyderabad" in work_text
    assert "dates: 2022-06-01 to 2024-12-31" in work_text
    # Description stays last so providers can treat the tail as free text.
    assert work_text.endswith("Built automated regression suites.")


def test_provider_receives_the_structured_fields() -> None:
    provider = FakeAIProvider(response_with())
    service = GenerationService(provider)

    service.generate(
        GenerationRequest(
            job_context=JobContext(
                job_title="SDET",
                description="Python testing role.",
                requirements=("Python",),
            ),
            approved_evidence=from_grounding_contexts(
                [SKILL_CONTEXT, CERTIFICATION_CONTEXT, WORK_CONTEXT]
            ),
        ),
        user_id=uuid4(),
    )

    sent = provider.last_request
    assert sent is not None
    prompt = " ".join(item.text for item in sent.evidence)
    assert "proficiency: Advanced" in prompt
    assert "credential: CTFL-2023-44810" in prompt
    # Still no database identifiers in what the provider sees.
    assert str(SKILL_CONTEXT.evidence_id) not in prompt


def test_demo_provider_writes_something_real_for_skill_and_certification() -> None:
    from app.services.ai.demo import DemoAIProvider

    service = GenerationService(DemoAIProvider())

    result = service.generate(
        GenerationRequest(
            job_context=JobContext(
                job_title="SDET",
                description="Python testing role.",
                requirements=("Python",),
            ),
            approved_evidence=from_grounding_contexts([SKILL_CONTEXT, CERTIFICATION_CONTEXT]),
        ),
        user_id=uuid4(),
    )

    texts = " ".join(statement.text for statement in result.statements)
    assert "Python" in texts
    assert "CTFL-2023-44810" in texts or "ISTQB" in texts
    for statement in result.statements:
        assert statement.evidence_ids
