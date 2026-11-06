"""F15 interview defensibility service.

The check is deterministic on purpose. F07 and F11 ask a language model for
prose and then distrust what comes back; F15 asks nothing of a model at all.
Every signal it raises is a textual comparison between a statement the user
approved and the evidence that statement cites, so the same inputs always
produce the same advice, the result can be explained to the user line by
line, and the feature works today without F08, F09 or a provider.

Flow:
1. Receive approved statements plus the evidence they cite, already resolved
   from F02 by the route.
2. For each statement, compare its specifics against the cited evidence.
3. Raise a signal for every specific the evidence does not contain.
4. Turn the statement and its signals into questions the user should expect.
5. Draw supporting points from the evidence, never from new prose.

What this is not: a verification. F08 owns VERIFIED / INFERRED / UNSUPPORTED
and F09 owns approval. A HARD_TO_DEFEND result here means "an interviewer
would press you on this and your evidence does not answer it", which is
advice, not a gate.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from .cover_letter_schemas import ApprovedStatement
from .errors import GenerationError
from .interview_schemas import (
    MAX_QUESTION_LENGTH,
    MAX_QUESTIONS_PER_STATEMENT,
    MAX_SIGNAL_DETAIL_LENGTH,
    MAX_SUPPORTING_POINT_LENGTH,
    DefensibilityRisk,
    InterviewPrep,
    InterviewPrepRequest,
    InterviewQuestion,
    QuestionKind,
    RiskSignal,
    SignalCode,
    StatementPreparation,
)
from .schemas import GenerationEvidence

# A claim is "thin" when everything the user wrote about the cited evidence
# would not fill a short paragraph. Below this there is simply not enough
# material to answer a follow-up question from.
THIN_EVIDENCE_CHARS = 80

MAX_SUPPORTING_POINTS = 4

# Quantities an interviewer can ask the source of: 40%, $2M, 12, 3.5x.
_NUMBER = re.compile(r"\$?\d[\d,]*(?:\.\d+)?\s*(?:%|x\b|k\b|m\b|bn\b)?", re.IGNORECASE)

# Claims of rank or uniqueness. Each is only a problem when the evidence does
# not say the same thing.
_SUPERLATIVES = (
    "first", "only", "best", "largest", "biggest", "fastest", "highest",
    "leading", "top", "unprecedented", "industry-leading",
)

# Claims of scope and authority over other people or a whole system.
_LEADERSHIP = (
    "led", "leading", "managed", "managing", "owned", "directed", "headed",
    "supervised", "mentored", "architected", "spearheaded",
)


class MissingEvidenceForStatementError(GenerationError):
    """A statement cites evidence the caller did not resolve.

    The route resolves every cited id through F02 before calling the service,
    so this is a programming error rather than something a user can trigger.
    It is raised rather than ignored: analysing a claim against only part of
    its evidence would report confident nonsense.
    """


def _normalize(text: str) -> str:
    """Lowercase and strip separators so "1,200" and "1200" compare equal."""
    return re.sub(r"[,\s]+", " ", text.lower()).strip()


def _numeric_tokens(text: str) -> list[str]:
    """Every quantity in ``text``, normalized for comparison."""
    found: list[str] = []
    for match in _NUMBER.finditer(text):
        token = _normalize(match.group()).replace(" ", "")
        if token and token not in found:
            found.append(token)
    return found


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z\-']*", text.lower()))


def _clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class InterviewPreparationService:
    def __init__(
        self,
        *,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._new_id = id_factory
        self._now = clock

    def prepare(
        self,
        request: InterviewPrepRequest,
        *,
        user_id: UUID,
        evidence_by_id: Mapping[UUID, GenerationEvidence],
    ) -> InterviewPrep:
        """Build preparation advice for ``user_id``.

        Identity is a keyword argument rather than a request field so the only
        way to supply it is from the authenticated session.
        """
        items = tuple(
            self._prepare_statement(statement, evidence_by_id)
            for statement in request.approved_statements
        )
        return InterviewPrep(
            prep_id=self._new_id(),
            user_id=user_id,
            generated_at=self._now(),
            items=items,
        )

    def _prepare_statement(
        self,
        statement: ApprovedStatement,
        evidence_by_id: Mapping[UUID, GenerationEvidence],
    ) -> StatementPreparation:
        cited = self._cited_evidence(statement, evidence_by_id)
        signals = self._signals(statement, cited)
        return StatementPreparation(
            statement_id=statement.statement_id,
            statement_text=statement.text,
            evidence_ids=statement.evidence_ids,
            risk=_risk_from(signals),
            signals=signals,
            questions=self._questions(statement, signals),
            supporting_points=_supporting_points(cited),
        )

    @staticmethod
    def _cited_evidence(
        statement: ApprovedStatement,
        evidence_by_id: Mapping[UUID, GenerationEvidence],
    ) -> tuple[GenerationEvidence, ...]:
        missing = [
            evidence_id
            for evidence_id in statement.evidence_ids
            if evidence_id not in evidence_by_id
        ]
        if missing:
            raise MissingEvidenceForStatementError(
                "Statement cites evidence that was not resolved."
            )
        return tuple(evidence_by_id[evidence_id] for evidence_id in statement.evidence_ids)

    def _signals(
        self,
        statement: ApprovedStatement,
        cited: Sequence[GenerationEvidence],
    ) -> tuple[RiskSignal, ...]:
        signals: list[RiskSignal] = []

        # Quantities are read from the raw evidence text: normalizing first
        # would split "1,200" into two tokens and report a sourced figure as
        # unsourced.
        raw_evidence = " | ".join(item.to_prompt_text() for item in cited)
        haystack = _normalize(raw_evidence)

        evidence_numbers = _numeric_tokens(raw_evidence)
        for token in _numeric_tokens(statement.text):
            if token not in evidence_numbers:
                signals.append(
                    RiskSignal(
                        code=SignalCode.UNSOURCED_NUMBER,
                        detail=_clip(token, MAX_SIGNAL_DETAIL_LENGTH),
                    )
                )

        statement_words = _words(statement.text)
        evidence_words = _words(haystack)

        for word in _SUPERLATIVES:
            if word in statement_words and word not in evidence_words:
                signals.append(
                    RiskSignal(code=SignalCode.UNSOURCED_SUPERLATIVE, detail=word)
                )

        has_stated_role = any(item.role or item.organization for item in cited)
        for word in _LEADERSHIP:
            if word in statement_words and word not in evidence_words and not has_stated_role:
                signals.append(
                    RiskSignal(code=SignalCode.UNSOURCED_LEADERSHIP, detail=word)
                )

        described = sum(len(item.description or "") for item in cited)
        if described < THIN_EVIDENCE_CHARS:
            signals.append(
                RiskSignal(
                    code=SignalCode.THIN_EVIDENCE,
                    detail=f"{described} characters of description across cited evidence",
                )
            )

        if statement.verification_status == "INFERRED":
            signals.append(
                RiskSignal(
                    code=SignalCode.INFERRED_STATEMENT,
                    detail="inferred rather than directly verified",
                )
            )

        if len(statement.evidence_ids) == 1:
            signals.append(
                RiskSignal(code=SignalCode.SINGLE_SOURCE, detail="one cited evidence item")
            )

        return tuple(signals)

    def _questions(
        self, statement: ApprovedStatement, signals: Sequence[RiskSignal]
    ) -> tuple[InterviewQuestion, ...]:
        """Baseline questions first, then one per distinct signal.

        Baselines come first so that a statement with no signals still has
        something to rehearse, and so the list never reads as pure criticism.
        """
        quoted = _clip(statement.text, 80)
        drafts: list[tuple[QuestionKind, str]] = [
            (
                QuestionKind.EVIDENCE_PROBE,
                f'Walk me through what you actually did here: "{quoted}"',
            ),
            (
                QuestionKind.OWNERSHIP,
                "What was your own contribution, as opposed to the team's?",
            ),
        ]

        seen: set[SignalCode] = set()
        for signal in signals:
            if signal.code in seen:
                continue
            seen.add(signal.code)
            drafts.append(_question_for(signal))

        questions: list[InterviewQuestion] = []
        for kind, text in drafts[:MAX_QUESTIONS_PER_STATEMENT]:
            questions.append(
                InterviewQuestion(
                    question_id=self._new_id(),
                    statement_id=statement.statement_id,
                    kind=kind,
                    text=_clip(text, MAX_QUESTION_LENGTH),
                )
            )
        return tuple(questions)


def _question_for(signal: RiskSignal) -> tuple[QuestionKind, str]:
    match signal.code:
        case SignalCode.UNSOURCED_NUMBER:
            return (
                QuestionKind.METRIC_SOURCE,
                f'Where does the figure "{signal.detail}" come from, and how was it '
                "measured? Your evidence does not record it.",
            )
        case SignalCode.UNSOURCED_SUPERLATIVE:
            return (
                QuestionKind.SPECIFICS,
                f'You describe this as "{signal.detail}". Compared with what, and who '
                "else was in scope?",
            )
        case SignalCode.UNSOURCED_LEADERSHIP:
            return (
                QuestionKind.OWNERSHIP,
                f'What did "{signal.detail}" involve day to day, and who was relying '
                "on you?",
            )
        case SignalCode.THIN_EVIDENCE:
            return (
                QuestionKind.SPECIFICS,
                "Can you give a concrete example? Your cited evidence is brief, so an "
                "interviewer will ask for detail you have not written down.",
            )
        case SignalCode.INFERRED_STATEMENT:
            return (
                QuestionKind.EVIDENCE_PROBE,
                "This was inferred rather than directly verified. Which part comes "
                "straight from your experience, and which part is interpretation?",
            )
        case SignalCode.SINGLE_SOURCE:
            return (
                QuestionKind.EVIDENCE_PROBE,
                "This rests on one piece of evidence. What else have you done that "
                "shows the same ability?",
            )
    raise AssertionError(f"no question defined for {signal.code}")  # pragma: no cover


def _risk_from(signals: Sequence[RiskSignal]) -> DefensibilityRisk:
    """Unsourced specifics are the serious case; thin material is a warning."""
    serious = {
        SignalCode.UNSOURCED_NUMBER,
        SignalCode.UNSOURCED_SUPERLATIVE,
        SignalCode.UNSOURCED_LEADERSHIP,
    }
    codes = {signal.code for signal in signals}
    if codes & serious:
        return DefensibilityRisk.HARD_TO_DEFEND
    if codes:
        return DefensibilityRisk.NEEDS_DETAIL
    return DefensibilityRisk.SUPPORTED


def _supporting_points(cited: Sequence[GenerationEvidence]) -> tuple[str, ...]:
    """Restate the cited evidence as talking points.

    Every point is assembled from fields the user already approved. Nothing
    here is generated prose, so rehearsing an answer cannot drift into
    inventing one.
    """
    points: list[str] = []
    for item in cited:
        parts = [item.title]
        if item.role:
            parts.append(f"as {item.role}")
        if item.organization:
            parts.append(f"at {item.organization}")
        if item.start_date or item.end_date:
            start = item.start_date.isoformat() if item.start_date else "unknown"
            end = item.end_date.isoformat() if item.end_date else "present"
            parts.append(f"({start} to {end})")
        headline = " ".join(parts)
        if item.description:
            headline = f"{headline}: {item.description}"
        points.append(_clip(headline, MAX_SUPPORTING_POINT_LENGTH))
        if len(points) >= MAX_SUPPORTING_POINTS:
            break
    return tuple(points)
