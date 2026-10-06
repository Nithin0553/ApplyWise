"""Deterministic English-language prototype; deliberately conservative about inference."""

import hashlib
import re

from .contracts import (
    AnalysisResult,
    Category,
    ExperienceExpectation,
    Importance,
    Requirement,
    SourceContext,
)

# Section labels are matched exactly, never by substring in a requirement sentence.
SECTIONS = {
    "requirements": (None, None),
    "qualifications": (None, None),
    "required": (Importance.CRITICAL, None),
    "required skills": (Importance.CRITICAL, Category.SKILL),
    "required qualifications": (Importance.CRITICAL, None),
    "minimum qualifications": (Importance.CRITICAL, None),
    "essential qualifications": (Importance.CRITICAL, None),
    "must have": (Importance.CRITICAL, None),
    "preferred": (Importance.PREFERRED, None),
    "preferred skills": (Importance.PREFERRED, Category.SKILL),
    "preferred qualifications": (Importance.PREFERRED, None),
    "nice to have": (Importance.PREFERRED, None),
    "optional": (Importance.OPTIONAL, None),
    "optional skills": (Importance.OPTIONAL, Category.SKILL),
    "responsibilities": (None, Category.RESPONSIBILITY),
    "key responsibilities": (None, Category.RESPONSIBILITY),
    "what you will do": (None, Category.RESPONSIBILITY),
    "what you'll do": (None, Category.RESPONSIBILITY),
    "skills": (None, Category.SKILL),
    "education": (None, Category.EDUCATION),
    "experience": (None, Category.EXPERIENCE),
}
IGNORE_SECTIONS = {
    "about us",
    "about the company",
    "company overview",
    "benefits",
    "what we offer",
    "compensation",
    "salary",
    "equal opportunity",
    "how to apply",
    "about the role",
}
IMPORTANCE_PATTERNS = {
    Importance.CRITICAL: r"\b(must|required|mandatory|essential)\b",
    Importance.PREFERRED: r"\b(preferred|preferably|desirable|nice[- ]to[- ]have)\b|\ba plus\b",
    Importance.OPTIONAL: r"\b(optional|not required|not mandatory)\b",
}
CATEGORY_PATTERNS = {
    Category.SKILL: (
        r"\b(python|java|javascript|typescript|sql|react|excel|aws|azure|docker|git|"
        r"communication|teamwork|proficien\w*|knowledge|familiarity|skills?|ability)\b|C\+\+|C#"
    ),
    Category.EDUCATION: r"\b(degree|bachelor\w*|master\w*|ph\.?d\.?|diploma|education|bsc|msc)\b",
    Category.EXPERIENCE: r"\b(experience|years?|months?|internship)\b",
    Category.RESPONSIBILITY: (
        r"^(?:you will |the candidate will |responsible for )?"
        r"(build|develop|design|maintain|implement|test|collaborate|lead|manage|support|"
        r"monitor|analyze|analyse|write|review|deliver|create)\b"
    ),
    Category.QUALIFICATION: (
        r"\b(certification|certified|licen[sc]e|clearance|authorized|authorised|"
        r"authorization|authorisation|travel|relocate|eligibility|eligible|citizen\w*|permit)\b"
    ),
}


class UnparseableDescription(ValueError):
    """Well-formed text without any identifiable role requirements."""


def _label(text):
    return text.strip().rstrip(":").lower().replace("–", " ").replace("-", " ")


def _importance(text, section_importance):
    # Negated obligation is optional, not critical. Keep other conflicts for review.
    scrubbed = re.sub(r"\bnot (required|mandatory)\b", "optional", text, flags=re.I)
    explicit = [
        key for key, pattern in IMPORTANCE_PATTERNS.items() if re.search(pattern, scrubbed, re.I)
    ]
    if len(explicit) > 1:
        return None, "conflicting"
    if explicit:
        return explicit[0], "explicit"
    if section_importance:
        return section_importance, "section"
    return None, "unspecified"


def _experience(text):
    # A number alone (e.g. "3 years") is not silently interpreted as a minimum.
    pattern = (
        r"(?P<prefix>at least\s+|minimum(?: of)?\s+|up to\s+)?"
        r"(?P<low>\d+(?:\.\d+)?)\s*(?:(?P<plus>\+)|"
        r"(?:-|–|to)\s*(?P<high>\d+(?:\.\d+)?))?\s*(?P<unit>years?|months?)\b"
    )
    found = list(re.finditer(pattern, text, re.I))
    if len(found) != 1:
        return None, bool(found)
    match = found[0]
    multiplier = 1 / 12 if match["unit"].lower().startswith("month") else 1
    low = float(match["low"]) * multiplier
    high = float(match["high"]) * multiplier if match["high"] else None
    if high is not None and high < low:
        return None, True
    prefix = (match["prefix"] or "").lower()
    return ExperienceExpectation(
        minimum_years=low
        if high is not None or match["plus"] or prefix.startswith(("at least", "minimum"))
        else None,
        maximum_years=high if high is not None else low if prefix.startswith("up to") else None,
        stated_years=low if high is None and not match["plus"] and not prefix else None,
        expression=match[0],
    ), False


def extract(text: str) -> AnalysisResult:
    requirements = []
    section = None
    section_importance = None
    section_category = None
    in_requirements = False
    ignore = False
    offset = 0
    for line_number, raw in enumerate(text.splitlines(keepends=True), 1):
        # Remove only list/heading markers while retaining positions in the original.
        prefix = re.match(r"^\s*(?:(?:[-*•]|\d+[.)]|#{1,6})\s+)?", raw)[0]
        content_start = len(prefix)
        content = raw[content_start:].strip()
        if not content:
            offset += len(raw)
            continue
        label = _label(content)
        if label in SECTIONS or label in IGNORE_SECTIONS:
            section = content.rstrip(":")
            ignore = label in IGNORE_SECTIONS
            in_requirements = not ignore
            section_importance, section_category = SECTIONS.get(label, (None, None))
            offset += len(raw)
            continue
        # Support "Required skills: Python, SQL" without losing source offsets.
        colon = content.find(":")
        if colon >= 0 and _label(content[:colon]) in SECTIONS:
            section = content[:colon]
            section_importance, section_category = SECTIONS[_label(section)]
            in_requirements, ignore = True, False
            content_start += colon + 1
            content = raw[content_start:]
        elif content.endswith(":"):
            # Unknown headings must not accidentally inherit a previous section's priority.
            section, section_importance, section_category = content[:-1], None, None
            in_requirements, ignore = False, False
            offset += len(raw)
            continue
        if ignore or re.match(r"^(job title|location|company|salary|job type):", content, re.I):
            offset += len(raw)
            continue
        # Semicolon clauses remain separate. Do not split decimal years, C# or Node.js.
        for segment in re.finditer(r"[^;\r\n]+", raw[content_start:]):
            fragment = segment[0]
            leading = len(fragment) - len(fragment.lstrip())
            value = fragment.strip()
            if not value:
                continue
            categories = [
                kind
                for kind, pattern in CATEGORY_PATTERNS.items()
                if re.search(pattern, value, re.I)
            ]
            explicit_signal = any(re.search(p, value, re.I) for p in IMPORTANCE_PATTERNS.values())
            if not categories and not in_requirements and not explicit_signal:
                continue
            if section_category and section_category not in categories:
                categories.append(section_category)
            unknown_category = not categories
            categories = categories or [Category.QUALIFICATION]
            importance, basis = _importance(value, section_importance)
            experience, complex_experience = _experience(value)
            reasons = []
            if basis == "unspecified":
                reasons.append("Importance is not stated; confirm it before matching.")
            if basis == "conflicting":
                reasons.append("Conflicting importance cues; review the original requirement.")
            if unknown_category:
                reasons.append("Unrecognized requirement type retained as qualification.")
            if re.search(r"\bor\b|and/or|equivalent", value, re.I):
                reasons.append("Alternatives are preserved together; do not require every option.")
            if complex_experience:
                reasons.append("Multiple or inconsistent experience amounts need human review.")
            start = offset + content_start + segment.start() + leading
            source = SourceContext(
                text=value,
                start=start,
                end=start + len(value),
                line=line_number,
                section=section,
            )
            normalized = " ".join(value.split())
            identifier = hashlib.sha256(f"{start}:{normalized}".encode()).hexdigest()[:12]
            requirements.append(
                Requirement(
                    id=f"JR-{identifier}",
                    text=normalized,
                    categories=categories,
                    importance=importance,
                    importance_basis=basis,
                    source=source,
                    experience=experience,
                    needs_review=bool(reasons),
                    review_reasons=reasons,
                )
            )
        offset += len(raw)
    if not requirements:
        raise UnparseableDescription(
            "No identifiable job requirements found. "
            "Include skills, qualifications or responsibilities."
        )
    warnings = [
        "Rule-based English prototype: review extracted requirements before downstream use."
    ]
    if any(r.needs_review for r in requirements):
        warnings.append("Some requirements need review; unspecified importance remains null.")
    return AnalysisResult(
        document_id=hashlib.sha256(text.encode()).hexdigest(),
        requirements=requirements,
        warnings=warnings,
    )
