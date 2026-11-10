"""F08's classifier and revision derivation.

Deterministic on purpose. F07 asks a language model for prose and distrusts
what comes back; F08 asks nothing of a model at all. Every decision here is a
textual comparison between a claim and the approved evidence cited for it, so
the same inputs always produce the same classification, the result can be
explained to the user by quoting what triggered it, and the component that
decides whether a claim is supported cannot itself hallucinate.

Calibration, and why the three classes are drawn where they are:

``UNSUPPORTED`` is reserved for **fabricated specifics that can be checked
objectively** — a figure or a ranking the evidence does not contain. These
block export under Req-Qual-Trace-2, so a false positive costs the user a true
claim on their resume. That is the expensive mistake, and the bar is set to
avoid it.

``INFERRED`` covers claims that are grounded — no invented specifics — but
whose wording goes beyond what the evidence literally says. Claims of scope
("led", "owned") without a role recorded in the evidence land here rather than
in UNSUPPORTED: scope language is interpretive, and the user may well be right.
INFERRED is approvable and exportable; it simply is not certified.

``VERIFIED`` requires both: no fabricated specifics, and the claim's own
content words substantially present in the evidence.

The matching is lexical, not semantic. "nearly half" against evidence recording
"40%" is not detected, and that is a deliberate bias toward silence over false
accusation.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from uuid import UUID

from .contracts import (
    EvidenceFacts,
    VerificationFinding,
    VerificationReason,
    VerificationStatus,
)

REVISION_PREFIX = "v1-"
REVISION_DIGEST_CHARS = 32

# A claim is VERIFIED only if at least this share of its content words appear
# in the cited evidence. Below it the claim is grounded but worded beyond the
# evidence, which is what INFERRED means.
COVERAGE_THRESHOLD = 0.6

# Objectively checkable fabrication: the claim states something the cited
# evidence simply does not contain. These block export. Everything else is a
# wording judgement and yields INFERRED, which stays exportable.
FABRICATION_REASONS = frozenset({
    VerificationReason.FIGURE_NOT_IN_EVIDENCE,
    VerificationReason.RANKING_NOT_IN_EVIDENCE,
    VerificationReason.ENTITY_NOT_IN_EVIDENCE,
    VerificationReason.DATE_OUTSIDE_EVIDENCE,
})

# Quantities an interviewer or a recruiter can ask the source of.
_NUMBER = re.compile(r"\$?\d[\d,]*(?:\.\d+)?\s*(?:%|x\b|k\b|m\b|bn\b)?", re.IGNORECASE)

_RANKINGS = (
    "first", "only", "best", "largest", "biggest", "fastest", "highest",
    "leading", "top", "unprecedented", "sole",
)

_SCOPE = (
    "led", "leading", "managed", "managing", "owned", "directed", "headed",
    "supervised", "mentored", "architected", "spearheaded",
)

# Words that carry no claim and would inflate coverage if counted.
_STOPWORDS = frozenset("""
a an and are as at be been by for from had has have in into is it its of on or
over per that the their there these this to use used using was were what when
which who with within across while also other more most new
""".split())


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _numeric_tokens(text: str) -> list[str]:
    """Every quantity in ``text``, normalized so "1,200" and "1200" match."""
    found: list[str] = []
    for match in _NUMBER.finditer(text):
        token = re.sub(r"[,\s]", "", match.group()).lower()
        if token and token not in found:
            found.append(token)
    return found


def _stem(word: str) -> str:
    """Crude suffix stripping so "automation" and "automated" compare equal.

    Deliberately not a real stemmer: the rule must stay explainable to a user
    looking at why their claim was classified the way it was.
    """
    for suffix in ("ation", "ations", "ing", "ers", "er", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _content_words(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z\-']*", text.lower())
    return {_stem(word) for word in words if word not in _STOPWORDS and len(word) > 2}


def _literal_words(text: str) -> set[str]:
    """Word tokens, lowercased but **not** stemmed.

    Named things must be compared literally: stemming turns "Kubernetes" into
    "Kubernete" and would let a near-miss match.
    """
    return set(re.findall(r"[a-z0-9][a-z0-9+#.\-']*", text.lower()))


def _named_entities(text: str) -> list[str]:
    """Proper nouns and acronyms a claim asserts: employers, tools, credentials.

    A capitalized word that is not the first word of a sentence is a name, not
    a wording choice. The first word of each sentence is skipped because its
    capital says nothing, and stopwords are skipped so a capitalized "The"
    mid-sentence does not count.
    """
    found: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-']*", sentence)
        for index, token in enumerate(tokens):
            if index == 0:
                continue  # sentence-initial capital carries no information
            if not token[0].isupper():
                continue
            lowered = token.lower().rstrip(".")
            if lowered in _STOPWORDS or len(lowered) < 2:
                continue
            if lowered not in found:
                found.append(lowered)
    return found


def _claimed_years(text: str) -> list[int]:
    return [int(match) for match in re.findall(r"\b(?:19|20)\d{2}\b", text)]


def _evidence_year_range(cited: Sequence[EvidenceFacts]) -> tuple[int, int] | None:
    """The span the cited evidence actually covers, or None if it records none.

    An open-ended record (no end date) extends to the latest approval year, so
    an ongoing role is never treated as having stopped.
    """
    years: list[int] = []
    for item in cited:
        if item.start_date:
            years.append(item.start_date.year)
        if item.end_date:
            years.append(item.end_date.year)
        elif item.start_date:
            years.append(item.approved_at.year)
    if not years:
        return None
    return min(years), max(years)


def evidence_text(item: EvidenceFacts) -> str:
    """Flatten one approved evidence record to the text F08 compares against."""
    parts = [f"{item.title}"]
    for value in (item.role, item.organization, item.location, item.skill_name,
                  item.proficiency, item.credential):
        if value:
            parts.append(str(value))
    if item.start_date:
        parts.append(item.start_date.isoformat())
    if item.end_date:
        parts.append(item.end_date.isoformat())
    if item.description:
        parts.append(item.description)
    return " | ".join(parts)


def classify(
    *,
    text: str,
    evidence_ids: Sequence[UUID],
    approved: Mapping[UUID, EvidenceFacts],
) -> tuple[VerificationStatus, tuple[VerificationFinding, ...]]:
    """Classify one claim against the approved evidence cited for it.

    ``approved`` holds only evidence that F02 currently reports as approved and
    owned by this user. A cited id missing from it means the evidence was
    edited away, unapproved or deleted, and the claim cannot be checked at all.
    """
    findings: list[VerificationFinding] = []

    missing = [str(eid) for eid in evidence_ids if eid not in approved]
    if missing:
        findings.append(
            VerificationFinding(
                reason=VerificationReason.EVIDENCE_NOT_AVAILABLE,
                detail=f"{len(missing)} cited item(s) are no longer approved evidence",
            )
        )
        return VerificationStatus.UNSUPPORTED, tuple(findings)

    cited = [approved[eid] for eid in evidence_ids]
    raw = " | ".join(evidence_text(item) for item in cited)
    haystack_words = _content_words(raw)
    evidence_literals = _literal_words(raw)
    evidence_numbers = _numeric_tokens(raw)

    # When the evidence records dates, years belong to the date check below and
    # not to the figure check: "in 2023" against a 2022-2024 role is a true
    # statement, even though the literal token "2023" appears nowhere.
    span = _evidence_year_range(cited)
    claimed_years = {str(year) for year in _claimed_years(text)} if span else set()

    for token in _numeric_tokens(text):
        if token in claimed_years:
            continue
        if token not in evidence_numbers:
            findings.append(
                VerificationFinding(
                    reason=VerificationReason.FIGURE_NOT_IN_EVIDENCE,
                    detail=token[:160],
                )
            )

    # A named employer, tool or credential the evidence never mentions is a
    # fabricated fact, not a wording choice. "at Google" is exactly as checkable
    # as "by 40%", and coverage scoring hides it: one unknown proper noun in a
    # well-covered sentence still scores above the VERIFIED threshold.
    for entity in _named_entities(text):
        if entity not in evidence_literals:
            findings.append(
                VerificationFinding(
                    reason=VerificationReason.ENTITY_NOT_IN_EVIDENCE,
                    detail=entity[:160],
                )
            )

    # A year outside the span the cited evidence records is a changed date.
    # Only checked when the evidence records dates at all; otherwise there is
    # nothing to compare against and silence is the honest answer.
    if span is not None:
        first, last = span
        for year in _claimed_years(text):
            if not first <= year <= last:
                findings.append(
                    VerificationFinding(
                        reason=VerificationReason.DATE_OUTSIDE_EVIDENCE,
                        detail=f"{year} is outside the evidence range {first}-{last}",
                    )
                )

    claim_words = {word for word in re.findall(r"[a-z][a-z\-']*", text.lower())}
    for word in _RANKINGS:
        if word in claim_words and _stem(word) not in haystack_words:
            findings.append(
                VerificationFinding(
                    reason=VerificationReason.RANKING_NOT_IN_EVIDENCE, detail=word
                )
            )

    if any(finding.reason in FABRICATION_REASONS for finding in findings):
        return VerificationStatus.UNSUPPORTED, tuple(findings)

    has_stated_role = any(item.role or item.organization for item in cited)
    for word in _SCOPE:
        if word in claim_words and _stem(word) not in haystack_words and not has_stated_role:
            findings.append(
                VerificationFinding(
                    reason=VerificationReason.SCOPE_NOT_IN_EVIDENCE, detail=word
                )
            )

    claim_content = _content_words(text)
    covered = claim_content & haystack_words
    coverage = len(covered) / len(claim_content) if claim_content else 0.0

    if findings or coverage < COVERAGE_THRESHOLD:
        uncovered = sorted(claim_content - haystack_words)[:5]
        findings.append(
            VerificationFinding(
                reason=VerificationReason.BEYOND_EVIDENCE_WORDING,
                detail=(
                    f"{int(coverage * 100)}% of the claim's words appear in the evidence"
                    + (f"; not found: {', '.join(uncovered)}" if uncovered else "")
                )[:160],
            )
        )
        return VerificationStatus.INFERRED, tuple(findings)

    findings.append(
        VerificationFinding(
            reason=VerificationReason.FULLY_COVERED,
            detail=f"{int(coverage * 100)}% of the claim's words appear in the evidence",
        )
    )
    return VerificationStatus.VERIFIED, tuple(findings)


def derive_revision(
    *,
    text: str,
    evidence_ids: Sequence[UUID],
    approved: Mapping[UUID, EvidenceFacts],
    status: VerificationStatus,
) -> str:
    """Derive the revision from everything material about the statement.

    Included: the claim text, the cited evidence ids, the current content and
    approval timestamp of each cited record, and the resulting classification.

    Deriving rather than storing is the whole point. F09 invalidates an
    approval when the revision moves, and F13 refuses to export a snapshot
    whose revision is no longer current. Both guarantees would be silently
    hollow if any code path could change what a claim says, or what backs it,
    without changing the revision. Here there is no such path: the revision is
    a function of the material, so it cannot fail to rotate.
    """
    parts: list[str] = [_normalize(text), status.value]
    for evidence_id in sorted(evidence_ids, key=str):
        item = approved.get(evidence_id)
        if item is None:
            parts.append(f"{evidence_id}:absent")
            continue
        parts.append(
            f"{evidence_id}:{evidence_text(item)}:{item.approved_at.isoformat()}"
        )
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return REVISION_PREFIX + digest[:REVISION_DIGEST_CHARS]
