"""#84 FIN-003 分成规则 CRUD、1146/1147、阶梯试算。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from tests.test_live import headers

client = TestClient(app)

SCOPE = {"platforms": ["DYS"], "accountIds": [84001], "ipGroupIds": []}
OTHER_SCOPE = {"platforms": ["KS"], "accountIds": [84001], "ipGroupIds": []}


def rule_body(**overrides):
    body = {
        "ruleName": "达人六成",
        "shareTarget": "DAREN",
        "baseType": "NET_PROFIT",
        "rateType": "FIXED",
        "fixedRate": 0.6,
        "scope": SCOPE,
        "priority": 10,
        "effectiveRange": {"from": "2026-10-01", "to": "2026-12-31"},
        "confirmConflict": False,
    }
    body.update(overrides)
    return body


def ladder_body(**overrides):
    body = rule_body(
        ruleName="团队阶梯",
        shareTarget="TEAM",
        rateType="LADDER",
        fixedRate=None,
        ladderConfig=[
            {"min": 0, "max": 10000, "rate": 0.1},
            {"min": 10000, "max": None, "rate": 0.2},
        ],
        priority=5,
    )
    body.update(overrides)
    return body


def test_fin_share_rule_crud_version_disable_keeps_share_result():
    auth = headers()
    token = uuid.uuid4().hex
    created = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(clientToken=token),
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]
    assert created.json()["data"]["version"] == 1
    assert created.json()["data"]["status"] == "ENABLED"
    assert created.json()["data"]["fixedRate"] == 0.6

    again = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(ruleName="不应新建", clientToken=token, fixedRate=0.2),
    )
    assert again.json()["code"] == 0
    assert again.json()["data"]["id"] == rule_id
    assert again.json()["data"]["ruleName"] == "达人六成"

    paired = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(ruleName="实名人四成", shareTarget="REALNAME", fixedRate=0.4, priority=8),
    )
    assert paired.json()["code"] == 0

    from app.core import SessionLocal
    from app.models import FinShareResult

    db = SessionLocal()
    try:
        share = FinShareResult(
            session_code="IMS20261008DYS0084",
            rule_id=rule_id,
            rule_name="手工分成",
            share_target="DAREN",
            target_ref_name="达人",
            share_base=10000,
            share_amount=6000,
            calc_detail={"formula": "keep"},
            status="PENDING_AUDIT",
            tenant_id=0,
        )
        db.add(share)
        db.commit()
        share_id = share.id
    finally:
        db.close()

    edited = client.put(
        f"/admin-api/ims/fin/share/rule/{rule_id}",
        headers=auth,
        json=rule_body(ruleName="达人六成修订"),
    )
    assert edited.json()["code"] == 0
    assert edited.json()["data"]["version"] == 2
    assert edited.json()["data"]["ruleName"] == "达人六成修订"
    assert edited.json()["data"]["id"] == rule_id

    db = SessionLocal()
    try:
        hit = db.get(FinShareResult, share_id)
        assert hit is not None
        assert hit.rule_name == "手工分成"
        assert float(hit.share_amount) == 6000
        assert hit.status == "PENDING_AUDIT"
        assert hit.rule_id == rule_id
    finally:
        db.close()

    listed = client.get(
        "/admin-api/ims/fin/share/rules",
        headers=auth,
        params={"shareTarget": "DAREN", "status": "ENABLED"},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1
    assert any(row["id"] == rule_id and row["version"] == 2 for row in listed.json()["data"]["list"])

    disabled = client.delete(f"/admin-api/ims/fin/share/rule/{rule_id}", headers=auth)
    assert disabled.json()["code"] == 0
    assert disabled.json()["data"] is None
    after = client.get("/admin-api/ims/fin/share/rules", headers=auth, params={"status": "DISABLED"})
    assert any(row["id"] == rule_id and row["status"] == "DISABLED" for row in after.json()["data"]["list"])
    db = SessionLocal()
    try:
        kept = db.get(FinShareResult, share_id)
        assert kept is not None
        assert kept.rule_name == "手工分成"
        assert float(kept.share_amount) == 6000
        assert kept.status == "PENDING_AUDIT"
    finally:
        db.close()


def test_fin_share_rule_1146_sum_boundary_and_1147_conflict():
    auth = headers()
    scope = {"platforms": ["JD"], "accountIds": [84111], "ipGroupIds": []}

    def body(**overrides):
        return rule_body(scope=scope, **overrides)

    single = client.post("/admin-api/ims/fin/share/rule", headers=auth, json=body(fixedRate=0.2, ruleName="单对象"))
    assert single.json()["code"] == 0
    assert client.delete(f"/admin-api/ims/fin/share/rule/{single.json()['data']['id']}", headers=auth).json()["code"] == 0

    zero = client.post("/admin-api/ims/fin/share/rule", headers=auth, json=body(fixedRate=0))
    assert zero.json()["code"] == 1146
    assert zero.json()["msg"] == "分成比例须在 0~100% 之间"
    over = client.post("/admin-api/ims/fin/share/rule", headers=auth, json=body(fixedRate=1.0001))
    assert over.json()["code"] == 1146
    assert over.json()["msg"] == "分成比例须在 0~100% 之间"
    edge = client.post("/admin-api/ims/fin/share/rule", headers=auth, json=body(fixedRate=1, ruleName="整额", shareTarget="TEAM"))
    assert edge.json()["code"] == 0
    assert client.delete(f"/admin-api/ims/fin/share/rule/{edge.json()['data']['id']}", headers=auth).json()["code"] == 0

    base = client.post("/admin-api/ims/fin/share/rule", headers=auth, json=body(fixedRate=0.6))
    assert base.json()["code"] == 0
    low = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=body(ruleName="差一", shareTarget="REALNAME", fixedRate=0.3999, priority=9),
    )
    assert low.json()["code"] == 0
    high = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=body(ruleName="超一", shareTarget="REALNAME", fixedRate=0.4001, priority=9),
    )
    assert high.json()["code"] == 1146
    assert "100.01%" in high.json()["msg"]
    assert client.delete(f"/admin-api/ims/fin/share/rule/{low.json()['data']['id']}", headers=auth).json()["code"] == 0
    exact = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=body(ruleName="实名人四成", shareTarget="REALNAME", fixedRate=0.4, priority=9),
    )
    assert exact.json()["code"] == 0

    clash = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=body(ruleName="达人冲突", fixedRate=0.6, priority=30),
    )
    assert clash.json()["code"] == 1147
    assert base.json()["data"]["id"] in clash.json()["data"]["conflictRuleIds"]
    forced = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=body(ruleName="达人冲突", fixedRate=0.6, priority=30, confirmConflict=True),
    )
    assert forced.json()["code"] == 0
    assert forced.json()["data"]["priority"] == 30

    other = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(ruleName="快手达人", fixedRate=0.6, scope=OTHER_SCOPE, priority=11),
    )
    assert other.json()["code"] == 0

    overlap = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=ladder_body(
            ladderConfig=[
                {"min": 0, "max": 100, "rate": 0.1},
                {"min": 50, "max": 200, "rate": 0.2},
            ]
        ),
    )
    assert overlap.json()["code"] == 1146
    assert "重叠" in overlap.json()["msg"]
    bad_rate = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=ladder_body(ladderConfig=[{"min": 0, "max": None, "rate": 1.2}]),
    )
    assert bad_rate.json()["code"] == 1146
    assert bad_rate.json()["msg"] == "分成比例须在 0~100% 之间"
    gap = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=ladder_body(
            ladderConfig=[
                {"min": 0, "max": 100, "rate": 0.1},
                {"min": 150, "max": None, "rate": 0.2},
            ]
        ),
    )
    assert gap.json()["code"] == 1146
    assert "不连续" in gap.json()["msg"]


def test_fin_share_simulate_fixed_and_ladder():
    auth = headers()
    created = client.post("/admin-api/ims/fin/share/rule", headers=auth, json=ladder_body())
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]
    simulated = client.post(
        "/admin-api/ims/fin/share/simulate",
        headers=auth,
        json={"ruleId": rule_id, "simulateBase": 15000},
    )
    body = simulated.json()
    assert body["code"] == 0
    assert body["data"]["shareAmount"] == 2000
    assert body["data"]["simulateBase"] == 15000
    assert [row["amount"] for row in body["data"]["calcDetail"]] == [1000, 1000]
    assert body["data"]["calcDetail"][0]["rateApplied"] == 0.1
    assert body["data"]["calcDetail"][1]["rateApplied"] == 0.2

    draft = client.post(
        "/admin-api/ims/fin/share/simulate",
        headers=auth,
        json={"draftRule": rule_body(fixedRate=0.25, shareTarget="TEAM", ruleName="草稿"), "simulateBase": 10000},
    )
    assert draft.json()["code"] == 0
    assert draft.json()["data"]["shareAmount"] == 2500
    assert draft.json()["data"]["calcDetail"][0]["range"] == "固定"

    illegal = client.post(
        "/admin-api/ims/fin/share/simulate",
        headers=auth,
        json={"draftRule": rule_body(fixedRate=1.5), "simulateBase": 100},
    )
    assert illegal.json()["code"] == 1146
    negative = client.post(
        "/admin-api/ims/fin/share/simulate",
        headers=auth,
        json={"ruleId": rule_id, "simulateBase": -1},
    )
    assert negative.json()["code"] == 1001
    missing = client.delete("/admin-api/ims/fin/share/rule/999999", headers=auth)
    assert missing.json()["code"] == 1504


def test_fin_share_rule_ip_group_scope_roundtrip_and_distinct():
    """IP 组属于适用范围。编辑回传后仍在；编号非法 1001；不同 IP 组不算 1147。"""
    auth = headers()
    scope = {"platforms": ["DYS"], "accountIds": [84088], "ipGroupIds": [88001, 88002]}
    created = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(ruleName="IP组规则", shareTarget="TEAM", fixedRate=1, priority=3, scope=scope),
    )
    assert created.json()["code"] == 0
    data = created.json()["data"]
    assert data["scope"]["ipGroupIds"] == [88001, 88002]
    rule_id = data["id"]

    edited = client.put(
        f"/admin-api/ims/fin/share/rule/{rule_id}",
        headers=auth,
        json=rule_body(ruleName="IP组规则修订", shareTarget="TEAM", fixedRate=1, priority=3, scope=scope),
    )
    assert edited.json()["code"] == 0
    assert edited.json()["data"]["version"] == 2
    assert edited.json()["data"]["scope"]["ipGroupIds"] == [88001, 88002]
    assert edited.json()["data"]["scope"]["accountIds"] == [84088]

    bad = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(
            ruleName="非法IP组",
            shareTarget="TEAM",
            fixedRate=1,
            priority=4,
            scope={"platforms": ["DYS"], "accountIds": [84088], "ipGroupIds": [0]},
        ),
    )
    assert bad.json()["code"] == 1001
    assert "编号" in bad.json()["msg"]

    other = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(
            ruleName="另一IP组",
            shareTarget="TEAM",
            fixedRate=1,
            priority=4,
            scope={"platforms": ["DYS"], "accountIds": [84088], "ipGroupIds": [88009]},
        ),
    )
    assert other.json()["code"] == 0
    assert other.json()["data"]["scope"]["ipGroupIds"] == [88009]


def test_fin_share_rule_enable_roundtrip_and_disabled_edit_keeps_bills():
    auth = headers()
    scope = {"platforms": ["OTA"], "accountIds": [86001], "ipGroupIds": []}
    created = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(ruleName="可再启用", shareTarget="TEAM", fixedRate=0.3, priority=4, scope=scope),
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]
    version = created.json()["data"]["version"]

    from app.core import SessionLocal
    from app.models import FinShareResult

    db = SessionLocal()
    try:
        share = FinShareResult(
            session_code="IMS20261008OTA0460",
            rule_id=rule_id,
            rule_name="手工分成",
            share_target="TEAM",
            target_ref_name="团队",
            share_base=1000,
            share_amount=300,
            calc_detail={"formula": "keep"},
            status="PENDING_AUDIT",
            tenant_id=0,
        )
        db.add(share)
        db.commit()
        share_id = share.id
    finally:
        db.close()

    disabled = client.delete(f"/admin-api/ims/fin/share/rule/{rule_id}", headers=auth)
    assert disabled.json()["code"] == 0
    edited = client.put(
        f"/admin-api/ims/fin/share/rule/{rule_id}",
        headers=auth,
        json=rule_body(ruleName="停用中修订", shareTarget="TEAM", fixedRate=0.25, priority=4, scope=scope),
    )
    assert edited.json()["code"] == 0
    assert edited.json()["data"]["status"] == "DISABLED"
    assert edited.json()["data"]["version"] == version + 1
    enabled = client.put(f"/admin-api/ims/fin/share/rule/{rule_id}/enable", headers=auth)
    assert enabled.json()["code"] == 0
    assert enabled.json()["data"]["status"] == "ENABLED"
    assert enabled.json()["data"]["version"] == version + 1
    again = client.put(f"/admin-api/ims/fin/share/rule/{rule_id}/enable", headers=auth)
    assert again.json()["code"] == 0
    assert again.json()["data"]["status"] == "ENABLED"

    assert client.delete(f"/admin-api/ims/fin/share/rule/{rule_id}", headers=auth).json()["code"] == 0
    blocked = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(ruleName="同基数占位", shareTarget="DAREN", fixedRate=0.9, priority=6, scope=scope),
    )
    assert blocked.json()["code"] == 0
    crowded = client.put(f"/admin-api/ims/fin/share/rule/{rule_id}/enable", headers=auth)
    assert crowded.json()["code"] == 1146

    db = SessionLocal()
    try:
        kept = db.get(FinShareResult, share_id)
        assert kept is not None
        assert kept.rule_name == "手工分成"
        assert float(kept.share_amount) == 300
        assert kept.status == "PENDING_AUDIT"
    finally:
        db.close()


def test_fin_share_rule_sum_is_per_base_and_shortfall_allowed():
    auth = headers()
    scope = {"platforms": ["WX"], "accountIds": [85021], "ipGroupIds": []}
    daren = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(
            ruleName="毛利达人一成",
            shareTarget="DAREN",
            baseType="GROSS_PROFIT",
            fixedRate=0.1,
            priority=10,
            scope=scope,
        ),
    )
    assert daren.json()["code"] == 0
    realname = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(
            ruleName="GMV实名人",
            shareTarget="REALNAME",
            baseType="GMV",
            fixedRate=0.02,
            priority=10,
            scope=scope,
        ),
    )
    assert realname.json()["code"] == 0
    over = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(
            ruleName="毛利超额",
            shareTarget="REALNAME",
            baseType="GROSS_PROFIT",
            fixedRate=0.95,
            priority=12,
            scope=scope,
        ),
    )
    assert over.json()["code"] == 1146
    assert "105.00%" in over.json()["msg"]
    short = client.post(
        "/admin-api/ims/fin/share/rule",
        headers=auth,
        json=rule_body(
            ruleName="毛利团队两成",
            shareTarget="TEAM",
            baseType="GROSS_PROFIT",
            fixedRate=0.2,
            priority=8,
            scope=scope,
        ),
    )
    assert short.json()["code"] == 0
