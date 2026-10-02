"""F01 contract test for F02/F13/F14 consumers.

This does not import or depend on any other feature module (none exist
yet). Instead it stands in for "a future owner-scoped feature service"
with a minimal local model, to prove the actual contract: a `User.id`
obtained from `get_current_user` is a native `uuid.UUID` that can be used
directly as an owner-scoping filter value against a column typed
`Uuid(as_uuid=True)` in another table -- no str(...)/UUID(...) conversion
required at the boundary, and no accidental str/UUID mismatch that would
silently match nothing.

When F02/F13/F14 land for real, this file can be deleted in favor of a
contract test that imports their actual models.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import Uuid as SAUuid
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class _FeatureBase(DeclarativeBase):
    """A separate declarative base, deliberately not the app's shared
    Base/metadata -- this table exists only for this contract test and
    must never be created against the real database.
    """


class _OwnerScopedResource(_FeatureBase):
    __tablename__ = "contract_test_owner_scoped_resource"

    id: Mapped[uuid.UUID] = mapped_column(
        SAUuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(SAUuid(as_uuid=True), nullable=False)


def _register_payload() -> dict[str, str]:
    return {
        "email": "contract.user@example.com",
        "password": "correct-horse-1",
        "full_name": "Contract User",
    }


def test_authenticated_user_id_can_scope_a_feature_query_directly(
    client: TestClient, db_session: Session
) -> None:
    _FeatureBase.metadata.create_all(bind=db_session.get_bind())

    register_response = client.post("/auth/register", json=_register_payload())
    assert register_response.status_code == 201
    token = register_response.json()["access_token"]

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    user_id = uuid.UUID(me_response.json()["id"])
    assert isinstance(user_id, uuid.UUID)

    db_session.add(_OwnerScopedResource(owner_id=user_id))
    db_session.commit()

    owned = (
        db_session.query(_OwnerScopedResource)
        .filter(_OwnerScopedResource.owner_id == user_id)
        .one_or_none()
    )
    assert owned is not None

    other_user_id = uuid.uuid4()
    not_owned = (
        db_session.query(_OwnerScopedResource)
        .filter(_OwnerScopedResource.owner_id == other_user_id)
        .one_or_none()
    )
    assert not_owned is None
