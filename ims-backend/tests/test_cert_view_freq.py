"""#67 · CERT-S-R3 查看频次：同一证件 1 小时内 10 次通过，第 11 次 1035。"""

import os
from datetime import timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"
os.environ.pop("IMS_USE_CLOUD_DB", None)

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.cert_view import BLOCK_MSG, VIEW_LIMIT
from app.core import SessionLocal, utcnow
from app.main import app
from app.models import CertViewLog

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _upload(auth: dict, holder: str, number: str):
    return client.post(
        "/admin-api/ims/cert/archive/upload",
        headers=auth,
        json={
            "holderName": holder,
            "certType": "IDCARD",
            "certNoPlain": number,
            "fileKey": "local/cert/upload",
            "issueDate": "2020-01-01",
            "expireDate": "2030-12-31",
        },
    )


def _approve(auth: dict, cert_id: int):
    return client.put(
        f"/admin-api/ims/cert/archive/{cert_id}/review",
        headers=auth,
        json={"action": "APPROVE"},
    )


def _view(auth: dict, cert_id: int):
    return client.get(f"/admin-api/ims/corp/resource/certificate/{cert_id}/view", headers=auth)


def test_cert_view_frequency_eleventh_returns_1035_and_hour_rolls():
    assert VIEW_LIMIT == 10
    auth = headers()
    created = _upload(auth, "频次证", "110101199001011067")
    body = created.json()
    assert body["code"] == 0, body
    cert_id = body["data"]["id"]
    assert _approve(auth, cert_id).json()["code"] == 0

    for _ in range(VIEW_LIMIT):
        view = _view(auth, cert_id)
        payload = view.json()
        assert payload["code"] == 0, payload
        assert "admin" in payload["data"]["watermarkText"].lower()
        assert "signedUrl" not in view.text

    blocked = _view(auth, cert_id)
    blocked_body = blocked.json()
    assert blocked_body["code"] == 1035
    assert blocked_body["msg"] == BLOCK_MSG
    assert "signedUrl" not in blocked.text
    again = _view(auth, cert_id)
    assert again.json()["code"] == 1035

    other = _upload(auth, "另一张证", "110101199001011068")
    other_body = other.json()
    assert other_body["code"] == 0, other_body
    other_id = other_body["data"]["id"]
    assert _approve(auth, other_id).json()["code"] == 0
    other_view = _view(auth, other_id)
    assert other_view.json()["code"] == 0, other_view.json()

    db = SessionLocal()
    try:
        oldest = db.scalar(select(CertViewLog).where(CertViewLog.cert_id == cert_id).order_by(CertViewLog.id.asc()))
        assert oldest is not None
        oldest.created_at = utcnow() - timedelta(minutes=61)
        db.commit()
        kept = db.scalar(
            select(CertViewLog.id).where(CertViewLog.cert_id == cert_id, CertViewLog.deleted == 0)
        )
        assert kept is not None
    finally:
        db.close()

    recovered = _view(auth, cert_id)
    assert recovered.json()["code"] == 0, recovered.json()
    locked = _view(auth, cert_id)
    assert locked.json()["code"] == 1035
