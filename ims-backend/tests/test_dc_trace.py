import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_dc_trace_entry_and_query():
    auth = headers()
    entry = client.get(
        "/admin-api/ims/dc/trace/entry",
        headers=auth,
        params={"entryType": "ACCOUNT", "keyword": "", "limit": 5},
    )
    assert entry.json()["code"] == 0
    assert isinstance(entry.json()["data"], list)

    items = entry.json()["data"]
    entry_id = items[0]["entryId"] if items else "1"
    entry_type = items[0]["entryType"] if items else "ACCOUNT"
    queried = client.post(
        "/admin-api/ims/dc/trace/query",
        headers=auth,
        json={
            "entryType": entry_type,
            "entryId": entry_id,
            "mode": "GRAPH",
            "pageNo": 1,
            "pageSize": 5,
        },
    )
    body = queried.json()
    assert body["code"] == 0
    assert "queryCostMs" in body["data"]
    assert "nodes" in body["data"]


def test_dc_trace_account_keyword_detail_mode():
    """#52 · E2E 种子账号 AC-E2E-FIN 入口 + DETAIL 模式（无种子时跳过断言入口命中）"""
    auth = headers()
    entry = client.get(
        "/admin-api/ims/dc/trace/entry",
        headers=auth,
        params={"entryType": "ACCOUNT", "keyword": "AC-E2E-FIN", "limit": 5},
    )
    assert entry.json()["code"] == 0
    items = entry.json()["data"]
    fin_hit = next((i for i in items if "AC-E2E-FIN" in (i.get("entryLabel") or "")), None)
    if not fin_hit:
        return
    queried = client.post(
        "/admin-api/ims/dc/trace/query",
        headers=auth,
        json={
            "entryType": fin_hit["entryType"],
            "entryId": fin_hit["entryId"],
            "mode": "DETAIL",
            "pageNo": 1,
            "pageSize": 10,
        },
    )
    body = queried.json()
    assert body["code"] == 0
    data = body["data"]
    assert "detailList" in data
    assert isinstance(data["detailList"].get("list"), list)
    assert data["detailList"]["total"] >= 1
    assert "code" not in data["detailList"]
    node_types = {n["nodeType"] for n in data["nodes"]}
    assert "ACCOUNT" in node_types
    assert "SESSION" in node_types


def test_dc_trace_session_detail_export_and_timeout():
    """#53 · 场次明细下钻 + XLSX/PDF 导出 + 1181 宽日期降级 + 1504"""
    from tests.test_fin import approved_session, confirm_cost_for_session

    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)
    detail_live = client.get(f"/admin-api/ims/live/register/{code}", headers=auth)
    assert detail_live.json()["code"] == 0
    account_id = str(detail_live.json()["data"]["accountId"])

    queried = client.post(
        "/admin-api/ims/dc/trace/query",
        headers=auth,
        json={"entryType": "ACCOUNT", "entryId": account_id, "mode": "DETAIL", "pageNo": 1, "pageSize": 10},
    )
    body = queried.json()
    assert body["code"] == 0
    listed = [row["sessionCode"] for row in body["data"]["detailList"]["list"]]
    assert code in listed

    detail = client.get(f"/admin-api/ims/dc/trace/detail/{code}", headers=auth)
    detail_body = detail.json()
    assert detail_body["code"] == 0
    assert detail_body["data"]["sessionCode"] == code
    assert detail_body["data"]["liveData"]["gmv"] == 100000.0
    assert detail_body["data"]["profit"]["netProfit"] == 81400.0
    amounts = {row["costItem"]: row["amount"] for row in detail_body["data"]["costDetail"]}
    assert amounts["ad"] == 5000.0
    assert detail_body["data"]["dataAsOf"]

    missing = client.get("/admin-api/ims/dc/trace/detail/NO-SUCH-SESSION", headers=auth)
    assert missing.json()["code"] == 1504

    exported = client.get(
        "/admin-api/ims/dc/trace/export",
        headers=auth,
        params={"entryType": "ACCOUNT", "entryId": account_id, "format": "XLSX"},
    )
    export_body = exported.json()
    assert export_body["code"] == 0
    assert export_body["data"]["expiresIn"] == 300
    download_url = export_body["data"]["downloadUrl"]
    assert download_url.startswith("/admin-api/ims/dc/trace/export/file?token=")
    file_resp = client.get(download_url, headers=auth)
    assert file_resp.status_code == 200
    assert code.encode() in file_resp.content
    assert b"queryCostMs" in file_resp.content

    pdf = client.get(
        "/admin-api/ims/dc/trace/export",
        headers=auth,
        params={"entryType": "SESSION", "entryId": code, "format": "PDF"},
    )
    assert pdf.json()["code"] == 0
    pdf_file = client.get(pdf.json()["data"]["downloadUrl"], headers=auth)
    assert pdf_file.status_code == 200
    assert pdf_file.content.startswith(b"%PDF")
    assert code.encode() in pdf_file.content

    bad_format = client.get(
        "/admin-api/ims/dc/trace/export",
        headers=auth,
        params={"entryType": "ACCOUNT", "entryId": account_id, "format": "CSV"},
    )
    assert bad_format.json()["code"] == 1001

    slow = client.post(
        "/admin-api/ims/dc/trace/query",
        headers=auth,
        json={
            "entryType": "ACCOUNT",
            "entryId": account_id,
            "mode": "DETAIL",
            "dateRange": ["2020-01-01", "2026-12-31"],
        },
    )
    slow_body = slow.json()
    assert slow_body["code"] == 1181
    assert "缩小" in slow_body["msg"]
    assert isinstance(slow_body["data"]["queryCostMs"], (int, float))


def _query_detail(auth: dict, entry_type: str, entry_id: str) -> dict:
    queried = client.post(
        "/admin-api/ims/dc/trace/query",
        headers=auth,
        json={"entryType": entry_type, "entryId": entry_id, "mode": "DETAIL", "pageNo": 1, "pageSize": 10},
    )
    body = queried.json()
    assert body["code"] == 0, body
    return body["data"]


def _entry_hit(auth: dict, entry_type: str, keyword: str, entry_id: str) -> dict:
    listed = client.get(
        "/admin-api/ims/dc/trace/entry",
        headers=auth,
        params={"entryType": entry_type, "keyword": keyword, "limit": 8},
    )
    body = listed.json()
    assert body["code"] == 0, body
    hit = next((item for item in body["data"] if item.get("entryId") == entry_id), None)
    assert hit is not None, body["data"]
    assert hit["entryType"] == entry_type
    assert isinstance(hit.get("hint"), str)
    return hit


def test_attach_drill_fields_stubs_missing_external():
    """外部资产 / IP 组缺失时明细仍可返回，标签用资产桩，IP 组留空。"""
    from types import SimpleNamespace

    from app.dc_trace import attach_drill_fields

    session = SimpleNamespace(session_code="IMS1", responsible_user_id=0, account_id=9)
    rows = [{"sessionCode": "IMS1", "assetIds": [42]}]
    attach_drill_fields(
        rows,
        [session],
        reports={},
        profits={},
        names={},
        groups={9: (0, "未归属IP组")},
        labels={},
        masked=False,
    )
    assert rows[0]["gmv"] is None
    assert rows[0]["netProfit"] is None
    assert rows[0]["responsibleUserId"] == 0
    assert rows[0]["responsibleUserName"] == ""
    assert rows[0]["ipGroupId"] == 0
    assert rows[0]["ipGroupName"] == ""
    assert rows[0]["assetLabels"] == ["资产#42"]


def test_dc_trace_person_responsible_asset_and_ip_group():
    """#88 · 实名人 / 责任人 / 资产 / IP 组入口搜到场次，并下钻明细。无关资产不回全量场次。"""
    from app.ops_db import ops_session
    from app.ops_models import IpGroup, PlatformAccount

    from tests.test_fin import approved_session

    auth = headers()
    code = approved_session(auth)
    live = client.get(f"/admin-api/ims/live/register/{code}", headers=auth).json()["data"]
    person_id = str(live["realnamePersonId"])
    person_name = live["realnameName"]
    responsible_id = str(live["responsibleUserId"])
    responsible_name = live["responsibleUserName"]
    asset_id = str(live["deviceAssetIds"][0])
    account_id = live["accountId"]
    assert person_name
    assert responsible_name

    missed = client.get(
        "/admin-api/ims/dc/trace/entry",
        headers=auth,
        params={"entryType": "PERSON", "keyword": "___no_such_person___", "limit": 5},
    )
    assert missed.json()["code"] == 0
    assert missed.json()["data"] == []

    person = _entry_hit(auth, "PERSON", person_name, person_id)
    assert person_name in person["entryLabel"]
    person_data = _query_detail(auth, "PERSON", person_id)
    assert code in [row["sessionCode"] for row in person_data["detailList"]["list"]]
    person_types = {node["nodeType"] for node in person_data["nodes"]}
    assert {"PERSON", "ACCOUNT", "SESSION", "ASSET"} <= person_types

    responsible = _entry_hit(auth, "RESPONSIBLE", responsible_name, responsible_id)
    assert responsible_name in responsible["entryLabel"]
    responsible_data = _query_detail(auth, "RESPONSIBLE", responsible_id)
    assert code in [row["sessionCode"] for row in responsible_data["detailList"]["list"]]

    asset = _entry_hit(auth, "ASSET", asset_id, asset_id)
    assert asset["entryId"] == asset_id
    asset_data = _query_detail(auth, "ASSET", asset_id)
    assert code in [row["sessionCode"] for row in asset_data["detailList"]["list"]]
    asset_nodes = [node for node in asset_data["nodes"] if node["nodeType"] == "ASSET"]
    assert any(node["nodeId"] == asset_id for node in asset_nodes)
    assert any(edge["toNodeId"] == code for edge in asset_data["edges"])

    ops = ops_session()
    try:
        account = ops.get(PlatformAccount, account_id)
        assert account is not None and account.ip_group_id
        group = ops.get(IpGroup, account.ip_group_id)
        assert group is not None and group.group_name
        group_id = str(group.id)
        group_name = group.group_name
    finally:
        ops.close()

    group_hit = _entry_hit(auth, "IP_GROUP", group_name, group_id)
    assert group_hit["entryLabel"] == group_name
    group_data = _query_detail(auth, "IP_GROUP", group_id)
    assert code in [row["sessionCode"] for row in group_data["detailList"]["list"]]

    listed = next(item for item in person_data["detailList"]["list"] if item["sessionCode"] == code)
    assert listed["gmv"] == 100000.0
    assert listed["responsibleUserId"] == int(responsible_id)
    assert listed["responsibleUserName"] == responsible_name
    assert int(asset_id) in listed["assetIds"]
    assert listed["assetLabels"]
    assert listed["ipGroupId"] == int(group_id)
    assert listed["ipGroupName"] == group_name

    detail = client.get(f"/admin-api/ims/dc/trace/detail/{code}", headers=auth).json()
    assert detail["code"] == 0
    roles = {row["roleType"]: row["userName"] for row in detail["data"]["persons"]}
    assert roles["RESPONSIBLE"] == responsible_name
    assert roles["REALNAME"] == person_name
    assert detail["data"]["ipGroupId"] == int(group_id)
    assert detail["data"]["ipGroupName"] == group_name
    assert detail["data"]["assetLabels"]
    assert len(detail["data"]["assetLabels"]) == len(detail["data"]["assetIds"])

    unrelated = _query_detail(auth, "ASSET", "999999999")
    assert unrelated["detailList"]["total"] == 0
    assert unrelated["detailList"]["list"] == []
    assert unrelated["nodes"] == []

    exported = client.get(
        "/admin-api/ims/dc/trace/export",
        headers=auth,
        params={"entryType": "PERSON", "entryId": person_id, "format": "XLSX"},
    )
    assert exported.json()["code"] == 0
    file_resp = client.get(exported.json()["data"]["downloadUrl"], headers=auth)
    assert file_resp.status_code == 200
    assert code.encode() in file_resp.content


def test_dc_trace_aggregate_cost_profit_and_perf_metrics():
    """#91 · 聚合四维、关系图成本/利润节点、审计留痕与 P95/慢查询。R9 金额脱敏，非 R1/R9 看不了性能页。"""
    from datetime import datetime

    from app.acct_seed import _ensure_cloned_user, ensure_acct_peer_user
    from app.core import SessionLocal
    from app.models import DcTraceLog
    from tests.test_fin import approved_session, confirm_cost_for_session

    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)
    live = client.get(f"/admin-api/ims/live/register/{code}", headers=auth).json()["data"]
    account_id = str(live["accountId"])
    person_id = str(live["realnamePersonId"])

    before = client.get("/admin-api/ims/dc/trace/perf-metrics", headers=auth)
    assert before.json()["code"] == 0
    before_count = before.json()["data"]["queryCount"]

    queried = client.post(
        "/admin-api/ims/dc/trace/query",
        headers=auth,
        json={"entryType": "ACCOUNT", "entryId": account_id, "mode": "DETAIL", "pageNo": 1, "pageSize": 10},
    )
    body = queried.json()
    assert body["code"] == 0
    nodes = {node["nodeType"]: node for node in body["data"]["nodes"] if node["nodeId"] in {
        f"cost:{code}",
        f"profit:{code}",
        code,
    } or node["nodeType"] in {"COST", "PROFIT"}}
    cost_node = next(node for node in body["data"]["nodes"] if node["nodeId"] == f"cost:{code}")
    profit_node = next(node for node in body["data"]["nodes"] if node["nodeId"] == f"profit:{code}")
    assert cost_node["nodeType"] == "COST"
    assert cost_node["metrics"]["totalCost"] == 16600.0
    assert profit_node["nodeType"] == "PROFIT"
    assert profit_node["metrics"]["netProfit"] == 81400.0
    assert profit_node["metrics"]["gmv"] == 100000.0
    edge_pairs = {(edge["fromNodeId"], edge["toNodeId"]) for edge in body["data"]["edges"]}
    assert (code, f"cost:{code}") in edge_pairs
    assert (f"cost:{code}", f"profit:{code}") in edge_pairs

    def aggregate(by: str, entry_type: str = "ACCOUNT", entry_id: str = account_id, date_range: str = ""):
        params = {"entryType": entry_type, "entryId": entry_id, "aggregateBy": by}
        if date_range:
            params["dateRange"] = date_range
        listed = client.get("/admin-api/ims/dc/trace/aggregate", headers=auth, params=params)
        payload = listed.json()
        assert payload["code"] == 0, payload
        return payload["data"]

    account_rows = aggregate("ACCOUNT")
    assert len(account_rows) == 1
    assert account_rows[0]["dimensionValue"] == account_id
    assert account_rows[0]["sessionCount"] == 1
    assert account_rows[0]["personCount"] == 1
    assert account_rows[0]["gmv"] == 100000.0
    assert account_rows[0]["totalCost"] == 16600.0
    assert account_rows[0]["netProfit"] == 81400.0

    person_rows = aggregate("PERSON", "PERSON", person_id)
    assert person_rows[0]["dimensionValue"] == person_id
    assert person_rows[0]["gmv"] == 100000.0
    assert person_rows[0]["netProfit"] == 81400.0

    group_rows = aggregate("IP_GROUP")
    assert len(group_rows) == 1
    assert group_rows[0]["dimensionLabel"]
    assert group_rows[0]["sessionCount"] == 1
    assert group_rows[0]["totalCost"] == 16600.0

    team_rows = aggregate("TEAM")
    assert len(team_rows) == 1
    assert team_rows[0]["sessionCount"] == 1
    assert team_rows[0]["netProfit"] == 81400.0
    assert team_rows[0]["dimensionLabel"]

    assert aggregate("ACCOUNT", date_range="2020-01-01,2020-01-02") == []
    kept = aggregate("ACCOUNT", date_range="2026-10-06,2026-10-06")
    assert kept[0]["sessionCount"] == 1

    bad_by = client.get(
        "/admin-api/ims/dc/trace/aggregate",
        headers=auth,
        params={"entryType": "ACCOUNT", "entryId": account_id, "aggregateBy": "MONTH"},
    )
    assert bad_by.json()["code"] == 1001
    wide = client.get(
        "/admin-api/ims/dc/trace/aggregate",
        headers=auth,
        params={"entryType": "ACCOUNT", "entryId": account_id, "aggregateBy": "ACCOUNT", "dateRange": "2020-01-01,2026-12-31"},
    )
    assert wide.json()["code"] == 1181

    after = client.get("/admin-api/ims/dc/trace/perf-metrics", headers=auth).json()["data"]
    assert after["queryCount"] >= before_count + 1
    assert after["targetP95Ms"] == 3000
    assert after["p99Ms"] >= after["p95Ms"]
    assert isinstance(after["dailyPressureTestPassed"], bool)
    assert isinstance(after["slowQueries"], list)

    db = SessionLocal()
    try:
        stamp = datetime(2030, 1, 1, 2, 0, 0)
        for cost_ms in [100, 200, 300, 400, 500, 600, 700, 800, 900, 4000]:
            db.add(
                DcTraceLog(
                    entry_type="ACCOUNT",
                    entry_id=account_id,
                    entry_label="压测样本",
                    query_user_id=1,
                    result_rows=1,
                    cost_ms=cost_ms,
                    tenant_id=0,
                    created_at=stamp,
                )
            )
        db.commit()
    finally:
        db.close()

    perf = client.get(
        "/admin-api/ims/dc/trace/perf-metrics",
        headers=auth,
        params={"dateRange": "2030-01-01,2030-01-01"},
    ).json()
    assert perf["code"] == 0
    assert perf["data"]["queryCount"] == 10
    assert perf["data"]["p95Ms"] == 4000
    assert perf["data"]["p99Ms"] == 4000
    assert perf["data"]["targetP95Ms"] == 3000
    assert perf["data"]["dailyPressureTestPassed"] is False
    assert len(perf["data"]["slowQueries"]) == 1
    assert perf["data"]["slowQueries"][0]["entryLabel"] == "压测样本"
    assert perf["data"]["slowQueries"][0]["costMs"] == 4000
    assert perf["data"]["slowQueries"][0]["queryId"].startswith("Q")
    assert perf["data"]["slowQueries"][0]["occurredAt"].startswith("2030-01-01")

    bad_range = client.get(
        "/admin-api/ims/dc/trace/perf-metrics",
        headers=auth,
        params={"dateRange": "2030-02-01,2030-01-01"},
    )
    assert bad_range.json()["code"] == 1001

    db = SessionLocal()
    try:
        ensure_acct_peer_user(db)
        _ensure_cloned_user(
            db,
            username="e2e_dc_r9",
            nickname="穿透数据分析师",
            mobile="13900000091",
            role_key="dc:r9",
            role_name="数据分析师",
        )
        db.commit()
    finally:
        db.close()

    peer = headers("e2e_acct_peer")
    denied = client.get("/admin-api/ims/dc/trace/perf-metrics", headers=peer)
    assert denied.status_code == 403
    assert denied.json()["code"] == 1008

    analyst = headers("e2e_dc_r9")
    allowed = client.get(
        "/admin-api/ims/dc/trace/perf-metrics",
        headers=analyst,
        params={"dateRange": "2030-01-01,2030-01-01"},
    )
    assert allowed.json()["code"] == 0
    masked = client.get(
        "/admin-api/ims/dc/trace/aggregate",
        headers=analyst,
        params={"entryType": "ACCOUNT", "entryId": account_id, "aggregateBy": "ACCOUNT"},
    ).json()
    assert masked["code"] == 0
    assert masked["data"][0]["gmv"] == 100000.0
    assert masked["data"][0]["totalCost"] is None
    assert masked["data"][0]["netProfit"] is None
    masked_graph = client.post(
        "/admin-api/ims/dc/trace/query",
        headers=analyst,
        json={"entryType": "ACCOUNT", "entryId": account_id, "mode": "GRAPH"},
    ).json()
    masked_cost = next(node for node in masked_graph["data"]["nodes"] if node["nodeId"] == f"cost:{code}")
    assert masked_cost["metrics"]["totalCost"] is None
    assert nodes  # 管理员图里成本/利润节点已取到
