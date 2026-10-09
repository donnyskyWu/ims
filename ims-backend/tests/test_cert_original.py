"""#138 · 证件原件上传桩：OCR 待确认、确认、按版本绑定且不覆盖旧文件。"""

import os
import uuid
from datetime import date, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.main import app
from app.cert_original import stored_path

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def upload_stub(auth: dict, text: str, name: str = "stub.txt"):
    return client.post(
        "/admin-api/ims/cert/archive/original",
        headers=auth,
        files={"file": (name, text.encode("utf-8"), "text/plain")},
    )


def test_original_upload_confirms_and_keeps_versions():
    auth = headers()
    holder = f"原件桩{uuid.uuid4().hex[:6]}"
    first = upload_stub(
        auth,
        "\n".join(
            [
                f"holderName={holder}",
                "certNo=110101199001011388",
                "issueDate=2021-06-01",
                "expireDate=2031-06-01",
            ]
        ),
    )
    body = first.json()
    assert body["code"] == 0, body
    assert body["data"]["version"] == 0
    assert body["data"]["ocrResult"]["recognizeStatus"] == "PENDING_CONFIRM"
    assert body["data"]["ocrResult"]["recognizedFields"]["holderName"] == holder
    assert ".." not in body["data"]["fileKey"]
    assert not body["data"]["fileKey"].startswith("/")
    first_key = body["data"]["fileKey"]
    first_sha = body["data"]["sha256"]
    first_path = stored_path(first_key)
    assert first_path is not None and first_path.is_file()

    empty = client.post(
        "/admin-api/ims/cert/archive/original",
        headers=auth,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert empty.json()["code"] == 1001

    binary = client.post(
        "/admin-api/ims/cert/archive/original",
        headers=auth,
        files={"file": ("scan.png", b"\x89PNG\r\n\x1a\nnot-text", "image/png")},
    )
    assert binary.json()["code"] == 0
    assert binary.json()["data"]["ocrResult"]["recognizeStatus"] == "FAILED"

    bad_action = client.post(
        "/admin-api/ims/cert/archive/original/confirm",
        headers=auth,
        json={"fileKey": first_key, "action": "REJECT"},
    )
    assert bad_action.json()["code"] == 1001

    confirmed = client.post(
        "/admin-api/ims/cert/archive/original/confirm",
        headers=auth,
        json={
            "fileKey": first_key,
            "action": "CONFIRM",
            "recognizedFields": {
                "holderName": holder,
                "certNo": "110101199001011388",
                "issueDate": "2021-06-01",
                "expireDate": "2031-06-01",
            },
        },
    )
    assert confirmed.json()["code"] == 0, confirmed.json()
    assert confirmed.json()["data"]["ocrResult"]["recognizeStatus"] == "CONFIRMED"

    created = client.post(
        "/admin-api/ims/cert/archive/upload",
        headers=auth,
        json={
            "holderName": holder,
            "certType": "IDCARD",
            "certNoPlain": "110101199001011388",
            "fileKey": first_key,
            "issueDate": "2021-06-01",
            "expireDate": (date.today() + timedelta(days=400)).isoformat(),
        },
    )
    created_body = created.json()
    assert created_body["code"] == 0, created_body
    cert_id = created_body["data"]["id"]

    bound = client.post(
        "/admin-api/ims/cert/archive/original/bind",
        headers=auth,
        json={"fileKey": first_key, "certId": cert_id},
    )
    assert bound.json()["code"] == 0, bound.json()
    assert bound.json()["data"]["version"] == 1

    second = upload_stub(auth, f"holderName={holder}\ncertNo=110101199001019999\nexpireDate=2032-01-01\n")
    second_body = second.json()
    assert second_body["code"] == 0, second_body
    second_key = second_body["data"]["fileKey"]
    assert second_key != first_key
    rebound = client.post(
        "/admin-api/ims/cert/archive/original/bind",
        headers=auth,
        json={"fileKey": second_key, "certId": cert_id},
    )
    assert rebound.json()["code"] == 0, rebound.json()
    assert rebound.json()["data"]["version"] == 2

    versions = client.post(
        "/admin-api/ims/cert/archive/original/versions",
        headers=auth,
        json={"certId": cert_id},
    )
    listed = versions.json()
    assert listed["code"] == 0, listed
    assert [item["version"] for item in listed["data"]["versions"]] == [1, 2]
    assert listed["data"]["versions"][0]["sha256"] == first_sha
    assert listed["data"]["versions"][0]["sha256"] != listed["data"]["versions"][1]["sha256"]
    second_path = stored_path(second_key)
    assert first_path.is_file()
    assert second_path is not None and second_path.is_file()
    assert first_path.read_bytes() != second_path.read_bytes()

    missing = client.post(
        "/admin-api/ims/cert/archive/original/bind",
        headers=auth,
        json={"fileKey": "cert/0/199901/missing.bin", "certId": cert_id},
    )
    assert missing.json()["code"] == 1504
