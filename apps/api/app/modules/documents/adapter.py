"""Convert trusted F13 content into an F10 renderable document."""

from __future__ import annotations

from app.modules.applications.schemas import ResumeVersionContent

from .schemas import ResumeDocument, ResumeEntry, ResumeSection, ResumeTemplate

_SECTION_FOR_TYPE = {
    "work_experience": "Experience",
    "education": "Education",
    "skill": "Skills",
    "certification": "Certifications",
    "project": "Projects",
    "responsibility": "Additional Experience",
    "accomplishment": "Additional Experience",
    "supporting_detail": "Additional Experience",
}
_SECTION_ORDER = (
    "Experience", "Education", "Skills", "Certifications", "Projects",
    "Additional Experience", "Additional Qualifications",
)


def build_resume_document(
    *,
    full_name: str,
    target_role: str,
    company: str | None,
    content: ResumeVersionContent,
    template: ResumeTemplate,
) -> ResumeDocument:
    """Map content from current_export_content(); this does not authorize export.

    Only evidence referenced by selected statements is included. Multi-source
    statements remain standalone to avoid attributing a combined claim to a
    single employer or degree. No facts are extracted from generated prose.
    """
    referenced = {eid for statement in content.statements for eid in statement.evidence_ids}
    grouped: dict[str, list[ResumeEntry]] = {}
    for evidence in content.evidence:
        if evidence.evidence_id not in referenced:
            continue
        statements = tuple(
            item for item in content.statements
            if item.evidence_ids == (evidence.evidence_id,)
        )
        heading = _SECTION_FOR_TYPE.get(evidence.evidence_type, "Additional Experience")
        title = evidence.title
        if evidence.evidence_type == "skill":
            title = evidence.skill_name or title
        elif evidence.evidence_type == "certification":
            title = evidence.credential or title
        grouped.setdefault(heading, []).append(ResumeEntry(
            evidence_ids=(evidence.evidence_id,),
            statement_ids=tuple(item.statement_id for item in statements),
            title=title,
            organization=evidence.organization,
            role=evidence.role,
            start_date=evidence.start_date,
            end_date=evidence.end_date,
            statements=tuple(item.text for item in statements),
        ))
    for statement in content.statements:
        if len(statement.evidence_ids) > 1:
            grouped.setdefault("Additional Qualifications", []).append(ResumeEntry(
                evidence_ids=statement.evidence_ids,
                statement_ids=(statement.statement_id,),
                statements=(statement.text,),
            ))
    return ResumeDocument(
        full_name=full_name,
        target_role=target_role,
        company=company,
        sections=tuple(
            ResumeSection(heading=heading, entries=tuple(grouped[heading]))
            for heading in _SECTION_ORDER if grouped.get(heading)
        ),
        template=template,
    )
