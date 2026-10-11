import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import ContentProject, ContentSop, DictData
from app.ops_db import ops_session
from app.ops_models import ExternalAccount, ExternalWork, InternalContent, IpGroup
from app.system_dict import align_dict_content_type, apply_content_type_compat, remap_stored_content_types

client = TestClient(app)



def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_external_works() -> None:
    ops = ops_session()
    try:
        group = IpGroup(group_name="竞品监测组", status="ENABLED", tenant_id=0)
        ops.add(group)
        ops.flush()
        ops.add_all(
            [
                ExternalWork(
                    platform_work_id="dy-hit-001",
                    title="对手爆款复盘",
                    account_name="竞品号A",
                    account_identifier="comp_a_ks",
                    platform_type="DOUYIN",
                    ip_group_id=group.id,
                    play_count=2_100_000,
                    like_count=88_000,
                    completion_rate=42.0,
                    publish_time="2026-10-01 18:00:00",
                    tenant_id=0,
                ),
                ExternalWork(
                    platform_work_id="ks-low-002",
                    title="对手日常更新",
                    account_name="竞品号B",
                    account_identifier="comp_b_ks",
                    platform_type="KUAISHOU",
                    ip_group_id=group.id,
                    play_count=45_000,
                    like_count=320,
                    completion_rate=9.5,
                    publish_time="2026-10-02 11:00:00",
                    tenant_id=0,
                ),
            ]
        )
        ops.commit()
    finally:
        ops.close()


def test_comp_work_page_all_and_hit():
    seed_external_works()
    auth = headers()
    all_resp = client.get(
        "/admin-api/ims/comp-analysis/work/page",
        headers=auth,
        params={"segment": "ALL", "pageNo": 1, "pageSize": 20},
    )
    body = all_resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 2
    assert any(row["isHit"] for row in body["data"]["list"])
    assert any(row["likeCount"] == 88_000 for row in body["data"]["list"])

    hit_resp = client.get(
        "/admin-api/ims/comp-analysis/work/page",
        headers=auth,
        params={"segment": "HIT", "pageNo": 1, "pageSize": 20},
    )
    hit_body = hit_resp.json()
    assert hit_body["code"] == 0
    assert hit_body["data"]["total"] == 1
    assert hit_body["data"]["list"][0]["title"] == "对手爆款复盘"


def seed_external_accounts() -> None:
    ops = ops_session()
    try:
        group = IpGroup(group_name="竞品账号组", status="ENABLED", tenant_id=0)
        ops.add(group)
        ops.flush()
        ops.add_all(
            [
                ExternalAccount(
                    account_identifier="comp_high_dy",
                    account_name="竞品高粉号",
                    platform_type="DOUYIN",
                    ip_group_id=group.id,
                    follower_count=520_000,
                    work_count=128,
                    last_synced_at="2026-10-05 09:00:00",
                    tenant_id=0,
                ),
                ExternalAccount(
                    account_identifier="comp_low_ks",
                    account_name="竞品低粉号",
                    platform_type="KUAISHOU",
                    ip_group_id=group.id,
                    follower_count=800,
                    work_count=12,
                    last_synced_at="2026-10-04 15:30:00",
                    tenant_id=0,
                ),
            ]
        )
        ops.commit()
    finally:
        ops.close()


def test_comp_account_page_all_and_high_fans():
    seed_external_accounts()
    auth = headers()
    all_resp = client.get(
        "/admin-api/ims/comp-analysis/account/page",
        headers=auth,
        params={"segment": "ALL", "pageNo": 1, "pageSize": 20},
    )
    body = all_resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 2
    assert any(row["isHighFans"] for row in body["data"]["list"])
    assert body["data"]["list"][0]["followerCount"] == 520_000
    assert body["data"]["list"][0]["rank"] == 1
    assert body["data"]["list"][0]["dailyNet"] is None

    high_resp = client.get(
        "/admin-api/ims/comp-analysis/account/page",
        headers=auth,
        params={"segment": "HIGH_FANS", "pageNo": 1, "pageSize": 20},
    )
    high_body = high_resp.json()
    assert high_body["code"] == 0
    assert high_body["data"]["total"] == 1
    assert high_body["data"]["list"][0]["accountName"] == "竞品高粉号"


def test_comp_account_low_fans_requires_threshold():
    seed_external_accounts()
    auth = headers()
    missing = client.get(
        "/admin-api/ims/comp-analysis/account/page",
        headers=auth,
        params={"segment": "LOW_FANS", "pageNo": 1, "pageSize": 20},
    )
    assert missing.json()["code"] == 1251

    created = client.post(
        "/admin-api/ims/collect/threshold",
        headers=auth,
        json={
            "thresholdCategory": "FANS",
            "platformType": "",
            "lowFans": 1000,
            "highFans": 100000,
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0

    low_resp = client.get(
        "/admin-api/ims/comp-analysis/account/page",
        headers=auth,
        params={"segment": "LOW_FANS", "pageNo": 1, "pageSize": 20},
    )
    low_body = low_resp.json()
    assert low_body["code"] == 0
    assert low_body["data"]["total"] == 1
    assert low_body["data"]["list"][0]["accountName"] == "竞品低粉号"


def test_comp_work_low_score_uses_br004_default():
    """BUG-B028：竞品低分 Tab 与内部作品同一根因，未配置阈值时按完播率 <20% 加载。"""
    seed_external_works()
    auth = headers()
    missing = client.get(
        "/admin-api/ims/comp-analysis/work/page",
        headers=auth,
        params={"segment": "LOW_SCORE", "pageNo": 1, "pageSize": 20},
    )
    missing_body = missing.json()
    assert missing_body["code"] == 0
    assert missing_body["data"]["total"] == 1
    assert missing_body["data"]["list"][0]["title"] == "对手日常更新"
    assert missing_body["data"]["list"][0]["isLowScore"] is True

    created = client.post(
        "/admin-api/ims/collect/threshold",
        headers=auth,
        json={
            "thresholdCategory": "WORK",
            "platformType": "",
            "hotValue": "1000000",
            "lowValue": "20",
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0

    low_resp = client.get(
        "/admin-api/ims/comp-analysis/work/page",
        headers=auth,
        params={"segment": "LOW_SCORE", "pageNo": 1, "pageSize": 20},
    )
    low_body = low_resp.json()
    assert low_body["code"] == 0
    assert low_body["data"]["total"] == 1
    assert low_body["data"]["list"][0]["title"] == "对手日常更新"


def test_comp_work_article_filter_and_summary():
    ops = ops_session()
    try:
        ops.add(
            ExternalWork(
                platform_work_id="article-001",
                title="图文测评",
                account_name="公众号竞品",
                platform_type="WECHAT_OFFICIAL",
                content_type="ARTICLE",
                play_count=20_000,
                like_count=300,
                completion_rate=0,
                publish_time="2026-10-03 09:00:00",
                tenant_id=0,
            )
        )
        ops.commit()
    finally:
        ops.close()
    auth = headers()
    resp = client.get(
        "/admin-api/ims/comp-analysis/work/page",
        headers=auth,
        params={"segment": "ALL", "contentType": "ARTICLE", "pageNo": 1, "pageSize": 10},
    )
    body = resp.json()
    assert body["code"] == 0, body
    assert body["data"]["total"] == 1
    assert body["data"]["list"][0]["rank"] == 1
    assert body["data"]["list"][0]["contentType"] == "ARTICLE"
    assert body["data"]["list"][0]["contentTypeLabel"] == "文章"
    assert body["data"]["summary"]["totalPlay"] == 20_000
    assert "avgShare" in body["data"]["summary"]


def test_comp_work_and_account_export_follow_filter():
    seed_external_works()
    seed_external_accounts()
    auth = headers()
    exported = client.get(
        "/admin-api/ims/comp-analysis/work/export",
        headers=auth,
        params={"segment": "HIT", "platformType": "DOUYIN"},
    )
    assert exported.status_code == 200
    assert exported.headers["x-export-rows"] == "1"
    assert "对手爆款复盘" in exported.text

    accounts = client.get(
        "/admin-api/ims/comp-analysis/account/export",
        headers=auth,
        params={"segment": "ALL", "accountName": "高粉"},
    )
    assert accounts.status_code == 200
    assert accounts.headers["x-export-rows"] == "1"
    assert "竞品高粉号" in accounts.text


def test_comp_work_rejects_retired_content_type():
    auth = headers()
    rejected = client.get(
        "/admin-api/ims/comp-analysis/work/page",
        headers=auth,
        params={"segment": "ALL", "contentType": "LIVE_CLIP", "pageNo": 1, "pageSize": 10},
    )
    body = rejected.json()
    assert body["code"] == 1503
    assert body["msg"] == "字典枚举非法"

    listed = client.get(
        "/admin-api/ims/system/dict-data/list",
        headers=auth,
        params={"dictType": "dict_content_type"},
    )
    enabled = [row for row in listed.json()["data"] if row["status"] == "ENABLED"]
    assert [(row["dictValue"], row["dictLabel"]) for row in enabled] == [
        ("ARTICLE", "文章"),
        ("SHORT_VIDEO", "短视频"),
        ("VIDEO", "视频"),
    ]


def test_content_type_remap_is_idempotent():
    db = SessionLocal()
    ops = ops_session()
    try:
        article = db.scalar(
            select(DictData).where(DictData.dict_type == "dict_content_type", DictData.dict_value == "ARTICLE")
        )
        assert article is not None
        article.dict_label = "图文"
        db.add(
            DictData(
                dict_type="dict_content_type",
                dict_label="直播切片",
                dict_value="LIVE_CLIP",
                sort=9,
                status="ENABLED",
                tenant_id=0,
            )
        )
        db.add(ContentProject(title="旧图文", content_type="GRAPHIC", submitter_user_id=1, tenant_id=0))
        db.add(ContentProject(title="旧图文码", content_type="IMAGE_TEXT", submitter_user_id=1, tenant_id=0))
        db.add(ContentProject(title="旧切片项目", content_type="直播切片", submitter_user_id=1, tenant_id=0))
        db.add(ContentProject(title="保持直播", content_type="LIVE", submitter_user_id=1, tenant_id=0))
        db.add(ContentSop(sop_code="LEGACY-IMG", sop_name="图文SOP", content_type="图文", tenant_id=0))
        ops.add(
            ExternalWork(
                platform_work_id="legacy-clip",
                title="切片",
                platform_type="DOUYIN",
                content_type="LIVE_CLIP",
                tenant_id=0,
            )
        )
        ops.add(
            ExternalWork(
                platform_work_id="legacy-tuwen",
                title="图文",
                platform_type="DOUYIN",
                content_type="图文",
                tenant_id=0,
            )
        )
        ops.add(
            ExternalWork(
                platform_work_id="keep-video",
                title="视频",
                platform_type="DOUYIN",
                content_type="VIDEO",
                tenant_id=0,
            )
        )
        ops.add(
            ExternalWork(
                platform_work_id="keep-live",
                title="直播",
                platform_type="KUAISHOU",
                content_type="直播",
                tenant_id=0,
            )
        )
        ops.add(InternalContent(title="内部切片", content_type="LIVE_CLIP", platform_type="DOUYIN", tenant_id=0))
        db.commit()
        ops.commit()

        align_dict_content_type(db)
        changed = remap_stored_content_types(db, ContentProject)
        changed += remap_stored_content_types(db, ContentSop)
        changed += remap_stored_content_types(ops, ExternalWork)
        changed += remap_stored_content_types(ops, InternalContent)
        assert changed == 7
        db.commit()
        ops.commit()
        db.expire_all()
        ops.expire_all()

        labels = {
            row.dict_value: (row.dict_label, row.status)
            for row in db.scalars(select(DictData).where(DictData.dict_type == "dict_content_type")).all()
        }
        assert labels["ARTICLE"] == ("文章", "ENABLED")
        assert labels["SHORT_VIDEO"] == ("短视频", "ENABLED")
        assert labels["VIDEO"] == ("视频", "ENABLED")
        assert labels["LIVE_CLIP"][1] == "DISABLED"

        stored = {
            row.title: row.content_type
            for row in ops.scalars(select(ExternalWork).where(ExternalWork.platform_work_id.like("legacy-%") | ExternalWork.platform_work_id.like("keep-%"))).all()
        }
        assert stored == {"切片": "SHORT_VIDEO", "图文": "ARTICLE", "视频": "VIDEO", "直播": "直播"}
        internal = ops.scalar(select(InternalContent).where(InternalContent.title == "内部切片"))
        assert internal is not None and internal.content_type == "SHORT_VIDEO"
        projects = {
            row.title: row.content_type
            for row in db.scalars(select(ContentProject)).all()
        }
        assert projects["旧图文"] == "ARTICLE"
        assert projects["旧图文码"] == "ARTICLE"
        assert projects["旧切片项目"] == "SHORT_VIDEO"
        assert projects["保持直播"] == "LIVE"
        sop = db.scalar(select(ContentSop).where(ContentSop.sop_code == "LEGACY-IMG"))
        assert sop is not None and sop.content_type == "ARTICLE"

        again = apply_content_type_compat(db, ops)
        assert again == 0
        db.commit()
        ops.commit()
    finally:
        db.close()
        ops.close()
