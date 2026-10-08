from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.models import DictData, DictType, SysParam, User
from app.settings_runtime import SECRET_MASK, invalidate_param_cache, is_secret_param, param_display_value

router = APIRouter()

DICT_SEED = [
    ("dict_platform_type", "平台", [("DOUYIN", "抖音"), ("KUAISHOU", "快手"), ("WECHAT_CHANNELS", "视频号"), ("WECHAT_OFFICIAL", "公众号"), ("XIAOHONGSHU", "小红书"), ("LEGACY_OFF", "已停用")]),
    ("dict_account_status", "账号状态", [("IN_USE", "在用"), ("IN_POOL", "池可领用"), ("FROZEN", "冻结"), ("RETURNED", "已归还"), ("CANCELLED", "已注销")]),
    ("dict_sop_node_type", "SOP 节点", [("WRITE", "撰写"), ("REVIEW", "审核"), ("PUBLISH", "发布")]),
    ("dict_document_type", "文档类型", [("SCRIPT", "脚本"), ("COPY", "文案")]),
    ("dict_marketing_plan_type", "营销计划", [("LIVE_PUBLIC", "直播公推"), ("PAID_SALES", "付费销售"), ("LIVE", "直播"), ("VIDEO", "短视频")]),
    ("dict_sales_platform", "销售平台", [("PRIVATE", "私域"), ("KUAISHOU", "快手"), ("DOUYIN", "抖音"), ("NONE", "无")]),
    ("dict_win_prediction", "红黑", [("RED", "红"), ("BLACK", "黑"), ("UNKNOWN", "待判定")]),
    ("dict_position", "钉钉岗位", [("LIVE_OPS", "直播运营"), ("DIRECTOR", "编导"), ("ANCHOR", "主播达人")]),
    ("dict_content_type", "内容类型", [("SHORT_VIDEO", "短视频"), ("LIVE_CLIP", "直播切片")]),
    ("dict_ai_scene", "AI 场景", [("TITLE", "标题"), ("COVER", "封面")]),
    ("dict_yes_no", "是否", [("YES", "是"), ("NO", "否")]),
    ("dict_sim_operator", "运营商", [("MOBILE", "移动"), ("UNICOM", "联通"), ("TELECOM", "电信")]),
    ("dict_sim_status", "手机卡状态", [("IN_USE", "在用"), ("IDLE", "闲置"), ("STOPPED", "停机"), ("CANCELLED", "注销"), ("DAMAGED", "损坏"), ("LOST", "丢失")]),
    ("dict_company_status", "公司状态", [("ENABLED", "启用"), ("DISABLED", "停用")]),
    ("dict_realname_status", "实名人状态", [("ENABLED", "启用"), ("DISABLED", "停用")]),
    ("dict_id_type", "证件类型", [("ID_CARD", "身份证"), ("PASSPORT", "护照"), ("HK_MACAO", "港澳通行证"), ("TAIWAN", "台湾通行证")]),
    ("dict_phone_status", "手机状态", [("IN_USE", "在用"), ("IDLE", "闲置"), ("DAMAGED", "损坏"), ("LOST", "丢失")]),
    ("dict_phone_type", "手机类型", [("ANDROID", "Android"), ("IPHONE", "iPhone")]),
    ("dict_collect_method", "采集方式", [("INTERNAL", "内部"), ("EXTERNAL", "外部竞品")]),
    ("dict_collect_frequency", "采集频率", [("HOURLY", "每小时"), ("DAILY", "每日"), ("WEEKLY", "每周")]),
    ("dict_collect_status", "采集任务状态", [("ENABLED", "启用"), ("DISABLED", "停用"), ("RUNNING", "运行中")]),
    ("dict_third_platform", "外部竞品平台", [("DOUYIN", "抖音"), ("KUAISHOU", "快手"), ("XIAOHONGSHU", "小红书")]),
    ("dict_match_type", "关键词匹配", [("EXACT", "精确"), ("CONTAINS", "包含"), ("FUZZY", "模糊")]),
    ("dict_threshold_category", "阈值类别", [("ALERT", "预警阈值"), ("FANS", "粉丝阈值"), ("WORK", "作品阈值"), ("OVERRIDE", "账号覆盖")]),
    ("dict_threshold_type", "阈值类型", [("PERCENT", "百分比"), ("ABSOLUTE", "绝对值")]),
    ("dict_metadata_entity_status", "元数据实体状态", [("ENABLED", "启用"), ("DISABLED", "停用")]),
    ("dict_metadata_query_condition_type", "查询条件类型", [("EQ", "等于"), ("LIKE", "模糊"), ("RANGE", "区间"), ("IN", "多选")]),
]

PARAM_SEED = [
    ("work.task.confirm.auto-ai-generate", "false", "工作任务确认后是否自动 AI（竞彩）"),
    ("content.review.levels", "2", "内容审核级数"),
    ("content.review.level1.enabled", "true", "一级审核开关"),
    ("content.review.level2.enabled", "true", "二级审核开关"),
    ("content.review.level1.role", "OPS_LEADER", "一级审核角色"),
    ("content.review.level2.role", "OPS_DIRECTOR", "二级审核角色"),
    ("air.key.ip_whitelist.enabled", "false", "Key IP 白名单总开关"),
    ("dingtalk.sso.enabled", "false", "钉钉登录开关"),
    ("bi.dingtalk.webhook.url", "", "BI 订阅钉钉群机器人 Webhook（空则 push-now 本地桩）"),
    ("dingtalk.corpId", "", "钉钉企业 CorpId（组织 L3 / 回调）"),
    ("dingtalk.clientId", "", "钉钉应用 Client ID（OAuth appKey）"),
    ("dingtalk.clientSecret", "", "钉钉应用 Client Secret（敏感，仅系统参数或本地 .env）"),
    ("dingtalk.agentId", "", "钉钉微应用 AgentId"),
    ("dingtalk.appId", "", "钉钉应用 AppId"),
    ("dingtalk.callbackToken", "", "钉钉事件回调 Token（验签）"),
    ("dingtalk.callbackAesKey", "", "钉钉事件回调 EncodingAESKey（43 位 Base64）"),
    ("dingtalk.l3Enabled", "false", "组织 L3 真钉钉联调（true/false；空则 corpId+Client 齐全时自动启用）"),
    (
        "football.webapiBaseUrl",
        "",
        "Football 生产 WebAPI 根地址（示例 https://saas.shenyu.com/；空则订单/文章桩）",
    ),
]


def seed_dict(db: Session) -> None:
    for dict_type, type_name, items in DICT_SEED:
        if db.scalar(select(DictType).where(DictType.dict_type == dict_type)) is None:
            db.add(DictType(dict_type=dict_type, type_name=type_name, status="ENABLED", tenant_id=0))
            for index, (value, label) in enumerate(items, start=1):
                status = "DISABLED" if value == "LEGACY_OFF" else "ENABLED"
                db.add(
                    DictData(
                        dict_type=dict_type,
                        dict_label=label,
                        dict_value=value,
                        sort=index,
                        status=status,
                        tenant_id=0,
                    )
                )
    for key, value, remark in PARAM_SEED:
        if db.scalar(select(SysParam).where(SysParam.param_key == key)) is None:
            db.add(SysParam(param_key=key, param_value=value, remark=remark, tenant_id=0))


def data_vo(row: DictData) -> dict:
    return {
        "id": row.id,
        "dictType": row.dict_type,
        "dictLabel": row.dict_label,
        "dictValue": row.dict_value,
        "sort": row.sort,
        "status": row.status,
    }


def param_vo(row: SysParam) -> dict:
    raw = row.param_value if row.param_value is not None else ""
    secret = is_secret_param(row.param_key)
    return {
        "paramKey": row.param_key,
        "paramValue": param_display_value(row.param_key, raw),
        "remark": row.remark,
        "secret": secret,
        "hasSecretValue": secret and bool(raw.strip()),
    }


class ParamBody(BaseModel):
    paramKey: str
    paramValue: str | bool | int | None = None


@router.get("/system/dict-type/list")
def dict_types(db: Session = Depends(db_session), _: User = Depends(current_user)):
    rows = db.scalars(select(DictType).where(DictType.deleted == 0).order_by(DictType.id)).all()
    data = []
    for row in rows:
        count = db.scalar(
            select(func.count(DictData.id)).where(DictData.dict_type == row.dict_type, DictData.deleted == 0)
        )
        data.append({"dictType": row.dict_type, "typeName": row.type_name, "status": row.status, "valueCount": count or 0})
    return ok(data)


@router.get("/system/dict-data/list")
def dict_data(dictType: str = "", db: Session = Depends(db_session), _: User = Depends(current_user)):
    stmt = select(DictData).where(DictData.deleted == 0)
    if dictType:
        stmt = stmt.where(DictData.dict_type == dictType)
    rows = db.scalars(stmt.order_by(DictData.sort, DictData.id)).all()
    return ok([data_vo(row) for row in rows])


@router.delete("/system/dict-data/{data_id}")
def delete_dict_data(data_id: int, db: Session = Depends(db_session), _: User = Depends(current_user)):
    row = db.get(DictData, data_id)
    if row is None or row.deleted:
        return fail(1504, "资源不可用")
    if row.status != "ENABLED":
        return fail(1503, "停用值不可删")
    row.deleted = 1
    return ok(None)


@router.get("/system/param")
def param_list(db: Session = Depends(db_session), _: User = Depends(current_user)):
    rows = db.scalars(select(SysParam).order_by(SysParam.id)).all()
    return ok([param_vo(row) for row in rows])


@router.put("/system/param")
def param_update(body: ParamBody, db: Session = Depends(db_session), _: User = Depends(current_user)):
    row = db.scalar(select(SysParam).where(SysParam.param_key == body.paramKey))
    if row is None:
        return fail(1213, "参数 key 未知")
    incoming = body.paramValue
    if is_secret_param(row.param_key):
        if incoming is None or str(incoming).strip() in ("", SECRET_MASK):
            return ok(param_vo(row))
    if isinstance(incoming, bool):
        row.param_value = "true" if incoming else "false"
    elif incoming is None:
        row.param_value = ""
    else:
        row.param_value = str(incoming)
    row.updated_at = utcnow()
    invalidate_param_cache()
    return ok(param_vo(row))
