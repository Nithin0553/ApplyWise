"""Convert trusted F13 content into an F10 renderable document."""

from __future__ import annotations

from app.modules.applications.schemas import ResumeVersionContent

from .schemas import ResumeDocument, ResumeTemplate


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
        template=template,
    )
