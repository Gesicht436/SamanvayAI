"""Regression tests for API authorization, tenant scoping, and transition guards."""

import uuid

import pytest
from fastapi import HTTPException

from api.security.jwt_auth import AuthUser, decode_access_token
from api.services.transfer import review_transfer_gate


def _run_immediate_coroutine(coro):
    """Run these route functions, which only await immediate in-memory operations."""
    try:
        coro.send(None)
    except StopIteration as result:
        return result.value
    raise AssertionError("Expected the coroutine to complete without external I/O")


def test_demo_token_cannot_select_role_tenant_or_domains():
    from api.routers.auth import DemoTokenRequest, generate_demo_token

    # Extra privilege claims are ignored by the request schema; the minted claims stay fixed.
    req = DemoTokenRequest.model_validate({"sub": "demo-user", "org_id": "VICTIM", "role": "ADMIN", "domains": ["POWER"]})
    result = generate_demo_token(req).model_dump()
    assert result["role"] == "MAKER"
    assert result["org_id"] == "OIL-1"
    user = decode_access_token(result["access_token"])
    assert user.role == "MAKER"
    assert user.org_id == "OIL-1"
    assert user.domains == ["COMMON"]


def test_demo_token_rejects_forged_subject():
    from api.routers.auth import DemoTokenRequest, generate_demo_token

    with pytest.raises(HTTPException) as exc:
        generate_demo_token(DemoTokenRequest(sub="someone-else"))
    assert exc.value.status_code == 400


def test_upload_limit_rejects_oversize_before_database_access(monkeypatch):
    from api import config
    from api.routers import ingest

    settings = config.Settings(jwt_secret="test-secret-for-api-unit-tests-minimum-32-characters", upload_max_mb=1)
    monkeypatch.setattr(ingest, "get_settings", lambda: settings)

    class FakeUpload:
        filename = "large.csv"

        async def read(self, size):
            return b"x" * size

    with pytest.raises(HTTPException) as exc:
        _run_immediate_coroutine(
            ingest.upload_document(
                file=FakeUpload(),
                doc_type="LEGACY_MASTER",
                current_user=AuthUser(sub="demo-user", org_id="OIL-1", role="MAKER"),
                db=None,
            )
        )
    assert exc.value.status_code == 413


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Transfer:
    id = uuid.uuid4()
    from_org = "OIL-1"
    to_org = "POWER-1"
    created_by = uuid.uuid4()
    state = "COMPLETED"


class _FakeSession:
    def __init__(self, transfer):
        self.transfer = transfer

    def execute(self, _statement):
        return _ScalarResult(self.transfer)


@pytest.mark.parametrize(
    "kwargs, status_code",
    [
        ({"current_org_id": "OTHER", "user_role": "CHECKER"}, 404),
        ({"current_org_id": "OIL-1", "user_role": "MAKER"}, 403),
        ({"current_org_id": "OIL-1", "user_role": "CHECKER"}, 409),
    ],
)
def test_transfer_review_rejects_wrong_tenant_role_or_terminal_transition(kwargs, status_code):
    with pytest.raises(HTTPException) as exc:
        review_transfer_gate(
            db=_FakeSession(_Transfer()),
            transfer_id=_Transfer.id,
            user_id=uuid.uuid4(),
            action="APPROVED",
            rationale="review",
            **kwargs,
        )
    assert exc.value.status_code == status_code


def test_demo_token_endpoint_is_disabled_when_demo_mode_off(monkeypatch):
    from api.config import Settings
    from api.routers import auth

    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: Settings(
            jwt_secret="test-secret-for-api-unit-tests-minimum-32-characters",
            demo_mode=False,
        ),
    )
    with pytest.raises(HTTPException) as exc:
        auth.generate_demo_token(auth.DemoTokenRequest())
    assert exc.value.status_code == 404


@pytest.mark.parametrize("secret", ["", "short", "replace-this-with-a-random-secret-of-at-least-32-characters"])
def test_runtime_rejects_missing_or_known_jwt_secrets(secret):
    from api.config import Settings

    with pytest.raises(ValueError):
        Settings(jwt_secret=secret).validate_runtime_security()


def test_steward_task_listing_query_scopes_tenant():
    from api.services.stewardship import list_steward_tasks

    class Result:
        def scalars(self):
            return self

        def all(self):
            return []

    class Session:
        statement = None

        async def execute(self, statement):
            self.statement = statement
            return Result()

    session = Session()
    _run_immediate_coroutine(list_steward_tasks(session, org_id="OIL-1"))
    sql = str(session.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "_org_id" in sql
    assert "OIL-1" in sql


def test_document_line_promotion_requires_document_tenant_match():
    from api.services.docs import promote_doc_line_to_raw_item

    class Result:
        def scalar_one_or_none(self):
            return None

    class Session:
        statement = None

        async def execute(self, statement):
            self.statement = statement
            return Result()

    session = Session()
    with pytest.raises(HTTPException) as exc:
        _run_immediate_coroutine(
            promote_doc_line_to_raw_item(
                session,
                document_id=uuid.uuid4(),
                doc_line_id=uuid.uuid4(),
                org_id="OIL-1",
            )
        )
    assert exc.value.status_code == 404
    sql = str(session.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "JOIN documents" in sql
    assert "documents.org_id = 'OIL-1'" in sql


@pytest.mark.parametrize("ids", [[], [uuid.uuid4(), uuid.uuid4()]])
def test_pool_creation_rejects_empty_or_duplicate_indent_ids(ids):
    from api.services.pool import create_tender_pool

    if len(ids) == 2:
        ids = [ids[0], ids[0]]

    class Session:
        def execute(self, _statement):
            raise AssertionError("Validation must fail before querying the database")

    with pytest.raises(HTTPException) as exc:
        create_tender_pool(Session(), "OIL-1", None, ids)
    assert exc.value.status_code == 400


def test_pool_creation_rejects_another_tenant_indent():
    from api.services.pool import create_tender_pool

    indent_id = uuid.uuid4()

    class Result:
        def scalars(self):
            return self

        def all(self):
            return [type("Indent", (), {"id": indent_id, "status": "OPEN", "org_id": "OTHER"})()]

    class Session:
        def execute(self, _statement):
            return Result()

    with pytest.raises(HTTPException) as exc:
        create_tender_pool(Session(), "OIL-1", None, [indent_id])
    assert exc.value.status_code == 403


def test_ingest_job_status_query_includes_tenant_predicate():
    from api.services.ingest import get_job_status

    class Result:
        def mappings(self):
            return self

        def first(self):
            return None

    class Session:
        statement = None
        params = None

        async def execute(self, statement, params):
            self.statement = statement
            self.params = params
            return Result()

    session = Session()
    assert _run_immediate_coroutine(get_job_status(session, 91, "OIL-1")) is None
    assert "payload->>'org_id' = :org_id" in str(session.statement)
    assert session.params["org_id"] == "OIL-1"


def test_ingest_job_stores_file_outside_json_and_rejects_path_escape(monkeypatch):
    import json
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from api.config import Settings
    from api.services import ingest

    class Result:
        def scalar_one(self):
            return 44

    class Session:
        params = None

        async def execute(self, _statement, params):
            self.params = params
            return Result()

        async def commit(self):
            return None

    with TemporaryDirectory(dir=".") as temp_dir:
        monkeypatch.setattr(
            ingest,
            "get_settings",
            lambda: Settings(
                jwt_secret="test-secret-for-api-unit-tests-minimum-32-characters",
                storage_path=temp_dir,
            ),
        )
        session = Session()
        job_id = _run_immediate_coroutine(
            ingest.enqueue_ingest_job(session, "OIL-1", b"csv,payload", "a.csv", "demo-user")
        )
        payload = json.loads(session.params["payload"])
        assert job_id == 44
        assert "file_b64" not in payload
        assert ingest._read_ingest_job_file(payload) == b"csv,payload"
        outside_path = Path(temp_dir).parent / f"{Path(temp_dir).name}_outside.bin"
        outside_path.write_bytes(b"leave untouched")
        with pytest.raises(ValueError):
            ingest._read_ingest_job_file({"file_path": str(outside_path)})
        ingest._remove_ingest_job_file({"file_path": str(outside_path)})
        assert outside_path.read_bytes() == b"leave untouched"
        outside_path.unlink()
