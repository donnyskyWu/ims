import os

os.environ.setdefault("IMS_DB", "ims_test_w5")
os.environ.setdefault("IMS_OPS_DB", "ims_ops_test_w5")

from app.crypto import encrypt_text
from app.main import app, init_db
from app.ops_db import ops_session
from app.ops_models import CollectorAccountBind, PlatformAccount
from fastapi.testclient import TestClient

init_db()
client = TestClient(app)
token = client.post(
    "/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}
).json()["data"]["accessToken"]
headers = {"Authorization": f"Bearer {token}"}

ops = ops_session()
acc = PlatformAccount(
    account_no="A1",
    account_name="T",
    platform_type="DOUYIN",
    status="IN_USE",
    tenant_id=0,
    cookie_enc=encrypt_text("x"),
)
ops.add(acc)
ops.flush()
ops.add(
    CollectorAccountBind(
        oa_account_id=acc.id,
        collector_account_id=f"acc_douyin_{acc.id}",
        bind_status="BOUND",
        conn_status="SUCCESS",
        tenant_id=0,
    )
)
ops.commit()
ops.close()

created = client.post(
    "/admin-api/ims/collect/task",
    headers=headers,
    json={
        "taskName": "smoke",
        "platformType": "DOUYIN",
        "accountId": acc.id,
        "frequency": "DAILY",
        "cron": "0 2 * * *",
        "status": "ENABLED",
    },
)
assert created.json()["code"] == 0, created.text
task_id = created.json()["data"]["id"]
run = client.post(f"/admin-api/ims/collect/task/{task_id}/run", headers=headers)
assert run.json()["code"] == 0, run.text
log_id = run.json()["data"]["logId"]
detail = client.get(f"/admin-api/ims/collect/log/{log_id}", headers=headers)
assert len(detail.json()["data"]["typeResults"]) >= 1
print("smoke_collect OK")
