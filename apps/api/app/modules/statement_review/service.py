"""F09 review state machine and server-controlled approved-statement provider.

A user decision is valid only for the exact *current* F08 verification
revision. This service cannot certify client-built snapshots or arbitrary
statement text, and it does not write into F08's module or F02's tables.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.generation.cover_letter_schemas import ApprovedStatement

from .contract import (
    CurrentVerificationProvider,
    CurrentVerifiedStatement,
    VerificationStatus,
)
from .models import ReviewDecision, StatementReviewEventRecord, StatementReviewRecord
from .schemas import (
    EffectiveReviewStatus,
    ReviewHistoryItem,
    StatementReviewView,
)


class ReviewNotFoundError(LookupError):
    """Unknown and foreign-owned statements share one error."""


class ReviewNotEligibleError(ValueError):
    """F08 did not certify this claim for approval."""


class StaleVerificationError(ValueError):
    """The user's expected verification revision is not current."""


class StatementReviewService:
    def __init__(self, session: Session, verifier: CurrentVerificationProvider):
        self.session = session
        self.verifier = verifier

    def _verified(self, *, user_id: UUID, statement_id: UUID) -> CurrentVerifiedStatement:
        candidate = self.verifier.get_current(user_id=user_id, statement_id=statement_id)
        if (
            candidate is None
            or candidate.user_id != user_id
            or candidate.statement_id != statement_id
        ):
            raise ReviewNotFoundError("Statement not found")
        return candidate

    def _record(
        self, *, user_id: UUID, statement_id: UUID, lock: bool = False
    ) -> StatementReviewRecord | None:
        statement = select(StatementReviewRecord).where(
            StatementReviewRecord.user_id == user_id,
            StatementReviewRecord.statement_id == statement_id,
        )
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    @staticmethod
    def _view(
        item: CurrentVerifiedStatement, record: StatementReviewRecord | None
    ) -> StatementReviewView:
        current = bool(record and record.verification_revision == item.revision)
        if record is None:
            review_status = EffectiveReviewStatus.UNREVIEWED
        elif not current:
            review_status = EffectiveReviewStatus.STALE
        elif record.decision == ReviewDecision.APPROVED:
            review_status = EffectiveReviewStatus.APPROVED
        else:
            review_status = EffectiveReviewStatus.REJECTED
        eligible = (
            current
            and record is not None
            and record.decision == ReviewDecision.APPROVED
            and item.status != VerificationStatus.UNSUPPORTED
        )
        return StatementReviewView(
            statement_id=item.statement_id,
            text=item.text,
            evidence_ids=item.evidence_ids,
            verification_status=item.status,
            verification_revision=item.revision,
            review_status=review_status,
            finalization_eligible=eligible,
            reviewed_revision=record.verification_revision if record else None,
        )

    def get_review(self, *, user_id: UUID, statement_id: UUID) -> StatementReviewView:
        current = self._verified(user_id=user_id, statement_id=statement_id)
        record = self._record(user_id=user_id, statement_id=statement_id)
        return self._view(current, record)

    def decide(
        self,
        *,
        user_id: UUID,
        statement_id: UUID,
        decision: ReviewDecision,
        expected_revision: str,
    ) -> StatementReviewView:
        current = self._verified(user_id=user_id, statement_id=statement_id)
        if current.revision != expected_revision:
            raise StaleVerificationError("Verification changed. Reload before reviewing.")
        if decision == ReviewDecision.APPROVED and current.status == VerificationStatus.UNSUPPORTED:
            raise ReviewNotEligibleError("UNSUPPORTED statements cannot be approved.")

        record = self._record(user_id=user_id, statement_id=statement_id, lock=True)
        if record is not None:
            if record.decision == decision and record.verification_revision == current.revision:
                return self._view(current, record)
            record.decision = decision
            record.verification_revision = current.revision
            record.event_count += 1
        else:
            record = StatementReviewRecord(
                user_id=user_id,
                statement_id=statement_id,
                decision=decision,
                verification_revision=current.revision,
                event_count=1,
            )
            self.session.add(record)
            self.session.flush()
        event = StatementReviewEventRecord(
            review_id=record.id,
            user_id=user_id,
            decision=decision,
            verification_revision=current.revision,
            sequence=record.event_count,
        )
        self.session.add(event)
        self.session.flush()
        return self._view(current, record)

    def carry_forward(self, *, user_id: UUID, statement_id: UUID) -> StatementReviewView:
        """Apply an approval this user already made for identical content.

        The revision is derived from the material: the claim's text, the
        evidence it cites, the current content and approval time of each cited
        record, and the classification. Two statements with the same revision
        are therefore the same assertion backed by the same evidence, whatever
        ids they carry. Regenerating a resume mints new statement ids for
        claims whose wording did not change, and without this the user is
        asked to approve sentences they have already approved, word for word,
        against the same records.

        This makes no new judgement. It looks for one of this user's own
        APPROVED reviews whose revision equals this statement's current
        revision and records the same decision here. Change the wording or the
        evidence by one character and the revision differs, so nothing is
        carried and the user is asked, which is the behaviour that matters.
        """
        current = self._verified(user_id=user_id, statement_id=statement_id)

        # Never carry an approval onto something F08 will not stand behind.
        # The status is part of the revision, so a match cannot be UNSUPPORTED;
        # this is here so that stops being true loudly rather than silently.
        if current.status == VerificationStatus.UNSUPPORTED:
            return self._view(current, self._record(user_id=user_id, statement_id=statement_id))

        record = self._record(user_id=user_id, statement_id=statement_id, lock=True)
        if record is not None and record.verification_revision == current.revision:
            return self._view(current, record)

        prior = self.session.scalar(
            select(StatementReviewRecord).where(
                StatementReviewRecord.user_id == user_id,
                StatementReviewRecord.statement_id != statement_id,
                StatementReviewRecord.decision == ReviewDecision.APPROVED,
                StatementReviewRecord.verification_revision == current.revision,
            )
        )
        if prior is None:
            return self._view(current, record)

        if record is None:
            record = StatementReviewRecord(
                user_id=user_id,
                statement_id=statement_id,
                decision=ReviewDecision.APPROVED,
                verification_revision=current.revision,
                event_count=1,
            )
            self.session.add(record)
            self.session.flush()
        else:
            record.decision = ReviewDecision.APPROVED
            record.verification_revision = current.revision
            record.event_count += 1

        self.session.add(StatementReviewEventRecord(
            review_id=record.id,
            user_id=user_id,
            decision=ReviewDecision.APPROVED,
            verification_revision=current.revision,
            carried_from_statement_id=prior.statement_id,
            sequence=record.event_count,
        ))
        self.session.flush()
        return self._view(current, record)

    def history(self, *, user_id: UUID, statement_id: UUID) -> tuple[ReviewHistoryItem, ...]:
        self._verified(user_id=user_id, statement_id=statement_id)
        record = self._record(user_id=user_id, statement_id=statement_id)
        if record is None:
            return ()
        events = self.session.scalars(
            select(StatementReviewEventRecord)
            .where(
                StatementReviewEventRecord.review_id == record.id,
                StatementReviewEventRecord.user_id == user_id,
            )
            .order_by(StatementReviewEventRecord.sequence)
        ).all()
        return tuple(ReviewHistoryItem.model_validate(event) for event in events)

    def list_approved_statements(
        self,
        *,
        user_id: UUID,
        statement_ids: tuple[UUID, ...] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[ApprovedStatement, ...]:
        """Owner-scoped, bounded read of currently approved F08 claims.

        F13 must be able to authorize an older saved resume: internal calls
        with no limit therefore return the complete current owner-scoped set.
        The HTTP route ALWAYS supplies a 1–20 limit. A restored journey can
        request explicit F08 IDs instead. All paths recompute F08 evidence
        and revision state before returning a claim.
        """
        if (limit is not None and not 1 <= limit <= 20) or not 0 <= offset <= 10_000:
            raise ValueError("Approved statement window is out of bounds.")
        if statement_ids is not None and len(statement_ids) > 20:
            raise ValueError("At most 20 statement IDs may be requested.")

        live = self.verifier.list_current(user_id=user_id)
        approved_query = select(StatementReviewRecord).where(
            StatementReviewRecord.user_id == user_id,
            StatementReviewRecord.decision == ReviewDecision.APPROVED,
        )
        if statement_ids is not None:
            approved_query = approved_query.where(
                StatementReviewRecord.statement_id.in_(statement_ids)
            )
        owned = self.session.scalars(approved_query).all()
        saved = {item.statement_id: item for item in owned}

        if statement_ids is None:
            # F08 lists the user's statements oldest first.
            candidates = reversed(live)
        else:
            by_id = {item.statement_id: item for item in live if item.user_id == user_id}
            candidates = (by_id[item_id] for item_id in dict.fromkeys(statement_ids)
                          if item_id in by_id)

        result: list[ApprovedStatement] = []
        matched = 0
        for item in candidates:
            if item.user_id != user_id or item.status == VerificationStatus.UNSUPPORTED:
                continue
            decision = saved.get(item.statement_id)
            if decision is None or decision.verification_revision != item.revision:
                continue
            if matched < offset:
                matched += 1
                continue
            result.append(
                ApprovedStatement(
                    statement_id=item.statement_id,
                    text=item.text,
                    evidence_ids=item.evidence_ids,
                    verification_status=item.status.value,
                    approval_status="APPROVED",
                )
            )
            if limit is not None and len(result) == limit:
                break
        return tuple(result)
