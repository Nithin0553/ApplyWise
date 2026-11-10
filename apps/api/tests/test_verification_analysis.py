"""F08 adversarial corpus: claims that try to pass as supported, and ones that
must not be punished for being true.

Both directions matter. A missed fabrication puts an invented number on a
resume. A false UNSUPPORTED blocks a true claim from export under
Req-Qual-Trace-2, which costs the user more than it costs us — so the
"must not be flagged" cases below are as load-bearing as the attacks.
"""

from __future__ import annotations

import pytest

from app.modules.verification.analysis import classify, derive_revision
from app.modules.verification.contracts import VerificationReason, VerificationStatus
from tests.fixtures.verification_fixtures import (
    APPROVED,
    MEASURED,
    MEASURED_ID,
    SKILL_ID,
    WORK,
    WORK_ID,
    FakeEvidence,
)


def verdict(text: str, ids=(WORK_ID, MEASURED_ID), approved=None):  # noqa: ANN001
    source = APPROVED if approved is None else approved
    return classify(text=text, evidence_ids=ids, approved=source)


def reasons(findings) -> set[VerificationReason]:  # noqa: ANN001
    return {item.reason for item in findings}


# --- fabricated figures: the headline requirement --------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Reduced regression runtime by 85%",
        "Cut defect escape rate by 3.5x",
        "Saved $2M in release costs",
        "Owned a suite of 1,200 automated tests",
    ],
)
def test_a_figure_absent_from_the_evidence_is_unsupported(text: str) -> None:
    status, findings = verdict(text)

    assert status is VerificationStatus.UNSUPPORTED
    assert VerificationReason.FIGURE_NOT_IN_EVIDENCE in reasons(findings)


def test_a_figure_the_evidence_records_is_not_flagged() -> None:
    """The evidence says 40%. Quoting it must not be called fabrication."""
    status, findings = verdict("Cut nightly regression runtime by 40%")

    assert VerificationReason.FIGURE_NOT_IN_EVIDENCE not in reasons(findings)
    assert status is not VerificationStatus.UNSUPPORTED


def test_a_comma_formatted_figure_matches_its_plain_form() -> None:
    """1,200 in the claim and 1200 in the evidence are the same number."""
    evidence = FakeEvidence(
        evidence_id=WORK_ID,
        evidence_type="project",
        title="Suite",
        role="QA Engineer",
        organization="Model N",
        description="Maintained 1200 automated regression tests for billing.",
    )
    status, findings = verdict(
        "Maintained 1,200 automated regression tests for billing",
        ids=(WORK_ID,),
        approved={WORK_ID: evidence},
    )

    assert VerificationReason.FIGURE_NOT_IN_EVIDENCE not in reasons(findings)
    assert status is VerificationStatus.VERIFIED


# --- fabricated rankings ---------------------------------------------------


def test_a_ranking_the_evidence_does_not_make_is_unsupported() -> None:
    status, findings = verdict("Delivered the first automated regression suite the team had")

    assert status is VerificationStatus.UNSUPPORTED
    assert VerificationReason.RANKING_NOT_IN_EVIDENCE in reasons(findings)


# --- scope claims are interpretive, not fabrication ------------------------


def test_scope_language_without_a_role_is_inferred_not_unsupported() -> None:
    """"Led" may well be true. It is not certified, but it is not blocked."""
    status, findings = verdict("Led the automation effort", ids=(SKILL_ID,))

    assert status is VerificationStatus.INFERRED
    assert VerificationReason.SCOPE_NOT_IN_EVIDENCE in reasons(findings)
    assert VerificationReason.FIGURE_NOT_IN_EVIDENCE not in reasons(findings)


def test_scope_language_backed_by_a_stated_role_is_not_flagged() -> None:
    status, findings = verdict("Led regression testing for revenue management software")

    assert VerificationReason.SCOPE_NOT_IN_EVIDENCE not in reasons(findings)
    assert status is not VerificationStatus.UNSUPPORTED


# --- the supported case ----------------------------------------------------


def test_a_claim_the_evidence_covers_is_verified() -> None:
    status, findings = verdict(
        "Built and maintained automated regression suites for revenue management software"
    )

    assert status is VerificationStatus.VERIFIED
    assert reasons(findings) == {VerificationReason.FULLY_COVERED}


def test_wording_beyond_the_evidence_is_inferred() -> None:
    """Grounded, nothing invented, but the words are the user's own."""
    status, _ = verdict("Improved release confidence for the billing organisation")

    assert status is VerificationStatus.INFERRED


# --- evidence that went away ----------------------------------------------


def test_a_claim_whose_evidence_is_no_longer_approved_is_unsupported() -> None:
    status, findings = verdict("Built automated regression suites", approved={})

    assert status is VerificationStatus.UNSUPPORTED
    assert VerificationReason.EVIDENCE_NOT_AVAILABLE in reasons(findings)


# --- the revision guarantee F09 and F13 rest on ----------------------------


def _revision(text: str, ids=(WORK_ID, MEASURED_ID), approved=None) -> str:  # noqa: ANN001
    source = APPROVED if approved is None else approved
    status, _ = classify(text=text, evidence_ids=ids, approved=source)
    return derive_revision(text=text, evidence_ids=ids, approved=source, status=status)


def test_the_same_claim_and_evidence_give_the_same_revision() -> None:
    assert _revision("Built automated regression suites") == _revision(
        "Built automated regression suites"
    )


def test_editing_the_claim_text_rotates_the_revision() -> None:
    assert _revision("Built automated regression suites") != _revision(
        "Built automated regression suites and CI pipelines"
    )


def test_editing_the_cited_evidence_rotates_the_revision() -> None:
    """The claim is untouched; only the evidence behind it changed."""
    before = _revision("Built automated regression suites")
    edited = dict(APPROVED)
    edited[WORK_ID] = FakeEvidence(
        evidence_id=WORK.evidence_id,
        evidence_type=WORK.evidence_type,
        title=WORK.title,
        organization=WORK.organization,
        role=WORK.role,
        description="Shadowed the regression suite owner.",
        start_date=WORK.start_date,
        end_date=WORK.end_date,
    )
    assert before != _revision("Built automated regression suites", approved=edited)


def test_re_approving_evidence_rotates_the_revision() -> None:
    """Same words, newer approval. F13's replay test depends on this."""
    from datetime import UTC, datetime

    before = _revision("Built automated regression suites")
    reapproved = dict(APPROVED)
    reapproved[WORK_ID] = FakeEvidence(
        evidence_id=WORK.evidence_id,
        evidence_type=WORK.evidence_type,
        title=WORK.title,
        organization=WORK.organization,
        role=WORK.role,
        description=WORK.description,
        start_date=WORK.start_date,
        end_date=WORK.end_date,
        approved_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
    )
    assert before != _revision("Built automated regression suites", approved=reapproved)


def test_changing_only_the_cited_set_rotates_the_revision() -> None:
    assert _revision("Built automated regression suites", ids=(WORK_ID,)) != _revision(
        "Built automated regression suites", ids=(WORK_ID, MEASURED_ID)
    )


def test_losing_the_evidence_rotates_the_revision() -> None:
    """Reclassification to UNSUPPORTED must not keep the old revision."""
    assert _revision("Built automated regression suites") != _revision(
        "Built automated regression suites", approved={}
    )


def test_the_revision_matches_the_format_f09_requires() -> None:
    import re

    value = _revision("Built automated regression suites")
    assert 8 <= len(value) <= 128
    assert re.fullmatch(r"^[a-zA-Z0-9._:-]+$", value)


def test_citation_order_does_not_change_the_revision() -> None:
    """Order is presentation, not substance; it must not look like an edit."""
    assert derive_revision(
        text="Built suites",
        evidence_ids=(WORK_ID, MEASURED_ID),
        approved=APPROVED,
        status=VerificationStatus.VERIFIED,
    ) == derive_revision(
        text="Built suites",
        evidence_ids=(MEASURED_ID, WORK_ID),
        approved=APPROVED,
        status=VerificationStatus.VERIFIED,
    )


def test_two_different_claims_do_not_collide() -> None:
    assert _revision("Built automated regression suites", ids=(MEASURED_ID,)) != _revision(
        "Reworked the nightly regression suite", ids=(MEASURED_ID,)
    )
    assert MEASURED.title  # fixture sanity


# --- fabricated named facts (employers, tools, credentials) ----------------
#
# Review of #69 found that these passed as VERIFIED and therefore exportable.
# A proper noun the evidence never mentions is a fabricated fact, not a wording
# choice, and coverage scoring hid it: one unknown name inside an otherwise
# well-covered sentence still scored above the VERIFIED threshold.


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("employer", "Built automated regression suites at Google for revenue management software"),
        ("tool", "Built automated regression suites with Kubernetes for revenue software"),
        ("credential", "Built automated regression suites certified by ISTQB for revenue software"),
        ("framework", "Built automated regression suites in Selenium for revenue software"),
    ],
)
def test_a_named_thing_absent_from_the_evidence_is_unsupported(name: str, text: str) -> None:
    status, findings = verdict(text)

    assert status is VerificationStatus.UNSUPPORTED, name
    assert VerificationReason.ENTITY_NOT_IN_EVIDENCE in reasons(findings), name


def test_a_named_employer_the_evidence_records_is_not_flagged() -> None:
    """Model N is in the evidence. Naming a real employer must stay clean."""
    status, findings = verdict(
        "Built automated regression suites at Model N for revenue management software"
    )

    assert VerificationReason.ENTITY_NOT_IN_EVIDENCE not in reasons(findings)
    assert status is VerificationStatus.VERIFIED


def test_a_named_skill_the_evidence_records_is_not_flagged() -> None:
    status, findings = verdict(
        "Advanced Python used for automated regression suites", ids=(WORK_ID, SKILL_ID)
    )

    assert VerificationReason.ENTITY_NOT_IN_EVIDENCE not in reasons(findings)


def test_a_sentence_initial_capital_is_not_treated_as_a_name() -> None:
    """The first word's capital says nothing about whether it is a proper noun."""
    status, findings = verdict(
        "Regression suites were built and maintained for revenue management software"
    )

    assert VerificationReason.ENTITY_NOT_IN_EVIDENCE not in reasons(findings)
    assert status is VerificationStatus.VERIFIED


def test_entity_matching_is_literal_not_stemmed() -> None:
    """Stemming would turn Kubernetes into Kubernete and let a near-miss pass."""
    status, findings = verdict("Built regression suites with Kubernete tooling")

    assert status is VerificationStatus.UNSUPPORTED
    assert VerificationReason.ENTITY_NOT_IN_EVIDENCE in reasons(findings)


# --- changed dates ---------------------------------------------------------


def test_a_year_outside_the_evidence_range_is_unsupported() -> None:
    """Evidence runs 2022-2024. Claiming 2018 is a changed date."""
    status, findings = verdict(
        "Built automated regression suites for revenue management software in 2018"
    )

    assert status is VerificationStatus.UNSUPPORTED
    assert VerificationReason.DATE_OUTSIDE_EVIDENCE in reasons(findings)


def test_a_year_inside_the_evidence_range_is_not_flagged() -> None:
    """2023 falls inside 2022-2024 and must not be read as an unsourced figure.

    The literal token "2023" appears nowhere in the evidence, so the figure
    check would flag it; years belong to the date check when the evidence
    records dates at all.
    """
    status, findings = verdict(
        "Built automated regression suites for revenue management software in 2023"
    )

    assert status is VerificationStatus.VERIFIED
    assert VerificationReason.DATE_OUTSIDE_EVIDENCE not in reasons(findings)
    assert VerificationReason.FIGURE_NOT_IN_EVIDENCE not in reasons(findings)


def test_a_year_is_still_checked_when_the_evidence_records_no_dates() -> None:
    """A skill record carries no dates, so a year claim cannot be substantiated."""
    status, findings = verdict("Advanced Python in 2023", ids=(SKILL_ID,))

    assert status is VerificationStatus.UNSUPPORTED
    assert VerificationReason.FIGURE_NOT_IN_EVIDENCE in reasons(findings)
