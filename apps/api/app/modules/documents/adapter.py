"""Convert trusted F13 content into an F10 renderable document."""

from __future__ import annotations

from app.modules.applications.schemas import (
    EvidenceSnapshotItem,
    ProvenanceSnapshotItem,
    ResumeVersionContent,
)

from .schemas import ResumeDocument, ResumeEntry, ResumeSection, ResumeTemplate

# Evidence type -> resume heading, in the order the headings appear on the
# page. The order is also the precedence used when one statement cites
# several kinds of evidence, so a responsibility cited alongside the job it
# belongs to is filed under that job rather than in a section of its own.
_SECTIONS: tuple[tuple[str, str], ...] = (
    ("work_experience", "Professional Experience"),
    ("project", "Projects"),
    ("education", "Education"),
    ("certification", "Certifications"),
    ("skill", "Technical Skills"),
)
_HEADINGS: dict[str, str] = dict(_SECTIONS)
_RANK: dict[str, int] = {name: index for index, (name, _) in enumerate(_SECTIONS)}
_UNRANKED = len(_SECTIONS)
_FALLBACK_HEADING = "Additional Experience"


def _primary_evidence(
    statement: ProvenanceSnapshotItem,
    by_id: dict,
) -> EvidenceSnapshotItem | None:
    """Return the cited record that decides where the statement is filed.

    Deterministic by construction: the highest-ranking evidence type among
    the records this statement cites, and among equal ranks the one the
    statement cites first. Nothing is inferred from the statement's wording.
    """
    cited = [by_id[eid] for eid in statement.evidence_ids if eid in by_id]
    if not cited:
        return None
    return min(cited, key=lambda item: _RANK.get(item.evidence_type, _UNRANKED))


def _build_sections(content: ResumeVersionContent) -> tuple[ResumeSection, ...]:
    """Group approved statements into resume sections by their provenance."""
    by_id = {item.evidence_id: item for item in content.evidence}

    # heading -> (organization, role) -> bullets, insertion-ordered so the
    # document keeps the order F13 approved the statements in.
    grouped: dict[str, dict[tuple[str | None, str | None], list[str]]] = {}

    for statement in content.statements:
        record = _primary_evidence(statement, by_id)
        heading = (
            _HEADINGS.get(record.evidence_type, _FALLBACK_HEADING)
            if record is not None
            else _FALLBACK_HEADING
        )
        key = (
            (record.organization, record.role)
            if record is not None
            else (None, None)
        )
        grouped.setdefault(heading, {}).setdefault(key, []).append(statement.text)

    ordered = sorted(
        grouped,
        key=lambda heading: next(
            (index for index, (_, name) in enumerate(_SECTIONS) if name == heading),
            _UNRANKED,
        ),
    )

    return tuple(
        ResumeSection(
            heading=heading,
            entries=tuple(
                ResumeEntry(organization=org, role=role, bullets=tuple(bullets))
                for (org, role), bullets in grouped[heading].items()
            ),
        )
        for heading in ordered
    )


def build_resume_document(
    *,
    full_name: str,
    target_role: str,
    company: str | None,
    content: ResumeVersionContent,
    template: ResumeTemplate,
) -> ResumeDocument:
    """Map server-validated F13 content into the F10 rendering contract.

    Callers must obtain content through F13's current_export_content().
    This adapter does not independently authorize exports.
    """
    return ResumeDocument(
        full_name=full_name,
        target_role=target_role,
        company=company,
        statements=tuple(item.text for item in content.statements),
        sections=_build_sections(content),
        template=template,
    )
