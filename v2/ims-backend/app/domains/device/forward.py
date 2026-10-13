"""正向穿透。账号、场次、成本层本批为空态，失败互不影响。"""
from __future__ import annotations

import time
from decimal import Decimal

from app.core.errors import BizError
from app.domains.device.ledger import holders, load
from app.domains.device.support import ASSET_STATUS, ASSET_TYPE, mask_keep, show_cost, user_brief
from app.domains.master.model import Realname
from app.db.session import get_session
from app.domains.resource.common import text_of

_LAYERS = ("L1", "L2", "L3", "L4", "L5")
_EMPTY = {
    "L2": "暂无绑定账号（账号模块上线后显示）",
    "L4": "暂无使用场次",
    "L5": "暂无成本数据（财务模块上线后显示）",
}


def _wanted(raw: str) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return list(_LAYERS)
    parts = [item.strip().upper() for item in text.split(",") if item.strip()]
    if not parts or any(item not in _LAYERS for item in parts):
        raise BizError(1013, "穿透层级超限（最多 5 层）")
    return parts


def detail(asset_id: int, params: dict) -> dict:
    started = time.perf_counter()
    layers = _wanted(text_of(params, "layers"))
    row = load(asset_id)
    cost = show_cost()
    if cost == "hidden":
        layers = [item for item in layers if item != "L5"]
    blocks = []
    for layer in layers:
        blocks.append(_layer(row, layer, cost))
    elapsed = int((time.perf_counter() - started) * 1000)
    _audit(row.id)
    return {"assetId": row.id, "elapsedMs": elapsed, "layers": blocks, "costMode": cost}


def _audit(asset_id: int) -> None:
    from app.core.context import get_ctx
    from app.domains.system.model import OperateLog

    ctx = get_ctx()
    get_session().add(
        OperateLog(
            operator_id=ctx.user_id if ctx else None,
            operator_name=(ctx.nickname or ctx.username) if ctx else "",
            module="资产穿透",
            action="查询",
            object_type="资产",
            object_id=str(asset_id),
            success=1,
            path="/admin-api/ims/asset/forward/detail",
            method="GET",
            params_digest="{}",
            tenant_id=ctx.tenant_id if ctx and ctx.tenant_id else 1,
            creator=ctx.user_id if ctx and ctx.user_id else 0,
        )
    )


def _layer(row, layer: str, cost: str) -> dict:
    if layer == "L1":
        owner = user_brief(row.owner_user_id)
        return {
            "layer": "L1",
            "title": "资产信息",
            "empty": "",
            "asset": {
                "assetCode": row.asset_code,
                "assetName": row.asset_name,
                "assetTypeLabel": ASSET_TYPE.get(row.asset_type, row.asset_type),
                "spec": row.spec or "",
                "statusLabel": ASSET_STATUS.get(row.status, row.status),
                "ownerName": owner["name"],
                "purchaseDate": row.purchase_date.isoformat() if row.purchase_date else "",
            },
        }
    if layer == "L2":
        return {"layer": "L2", "title": "绑定账号", "empty": _EMPTY["L2"], "accounts": []}
    if layer == "L3":
        people = []
        if row.realname_id:
            person = get_session().get(Realname, row.realname_id)
            if person is not None:
                people.append({"kind": "实名人", "name": person.name, "idNoMasked": mask_keep(person.id_no_enc)})
        for item in holders(row.id):
            people.append({"kind": "领用人", "name": item["userName"], "stateLabel": item["stateLabel"], "idNoMasked": ""})
        hint = ""
        if len(people) > 500:
            hint = "记录较多，请导出报告"
            people = people[:500]
        return {"layer": "L3", "title": "实名人", "empty": "" if people else "暂无实名人", "people": people, "hint": hint}
    if layer == "L4":
        from app.domains.live.guards import recent_sessions

        sessions = recent_sessions(row.id)
        return {"layer": "L4", "title": "使用场次", "empty": "" if sessions else _EMPTY["L4"], "sessions": sessions}
    from app.domains.live.guards import confirmed_cost

    spent = confirmed_cost(row.id)
    amount = "¥****" if cost == "masked" else spent["costTotal"]
    return {
        "layer": "L5",
        "title": "成本汇总",
        "empty": "" if cost == "masked" or Decimal(spent["costTotal"]) else _EMPTY["L5"],
        "costMasked": cost == "masked",
        "amount": amount,
        "adCost": "" if cost == "masked" else spent["adCost"],
        "items": [],
    }


def trace(asset_id: int, params: dict) -> dict:
    realname_raw = text_of(params, "realnameId")
    if int(asset_id or 0) == 0 and realname_raw:
        return _realname_trace(realname_raw)
    row = load(asset_id)
    nodes = [{"id": f"asset-{row.id}", "label": row.asset_code, "kind": "asset", "x": 80, "y": 40, "detail": _layer(row, "L1", "hidden")["asset"]}]
    edges = []
    if row.realname_id:
        person = get_session().get(Realname, row.realname_id)
        if person is not None:
            nodes.append({"id": f"rn-{person.id}", "label": person.name, "kind": "realname", "x": 80, "y": 120, "detail": {"name": person.name, "idNoMasked": mask_keep(person.id_no_enc)}})
            edges.append({"from": f"asset-{row.id}", "to": f"rn-{person.id}"})
    collapsed = False
    if len(nodes) > 100:
        nodes = nodes[:1]
        edges = []
        collapsed = True
    return {"rootId": f"asset-{row.id}", "nodes": nodes, "edges": edges, "collapsed": collapsed}


def _realname_trace(raw: str) -> dict:
    from app.core.serialize import parse_api_id
    from app.domains.device.model import AssetLedger

    ident = int(parse_api_id(raw))
    person = get_session().get(Realname, ident)
    if person is None or int(person.deleted or 0) != 0:
        raise BizError(1500, "关联的实名人不存在")
    rows = list(get_session().scalars(select_assets(ident)))
    nodes = [{"id": f"rn-{person.id}", "label": person.name, "kind": "realname", "x": 80, "y": 20, "detail": {"name": person.name, "idNoMasked": mask_keep(person.id_no_enc)}}]
    edges = []
    for index, row in enumerate(rows[:20]):
        nodes.append({"id": f"asset-{row.id}", "label": row.asset_code, "kind": "asset", "x": 40 + index * 30, "y": 120, "detail": {"assetCode": row.asset_code, "assetName": row.asset_name}})
        edges.append({"from": f"rn-{person.id}", "to": f"asset-{row.id}"})
    return {"rootId": f"rn-{person.id}", "nodes": nodes, "edges": edges, "collapsed": len(rows) > 100}


def select_assets(realname_id: int):
    from sqlalchemy import select

    from app.domains.device.model import AssetLedger

    return select(AssetLedger).where(AssetLedger.realname_id == int(realname_id))


def export_report(asset_id: int) -> dict:
    from app.domains.device.support import site_message, viewer_id
    from app.services.exchange import remember_binary

    data = detail(asset_id, {})
    lines = [f"穿透报告 {data['assetId']}", f"耗时 {data['elapsedMs']} 毫秒"]
    for block in data["layers"]:
        lines.append(block["title"])
        if block.get("empty"):
            lines.append(block["empty"])
        asset = block.get("asset") or {}
        if asset:
            lines.append(f"{asset.get('assetCode', '')} {asset.get('assetName', '')} {asset.get('statusLabel', '')}")
        for person in block.get("people") or []:
            lines.append(f"{person.get('kind', '')} {person.get('name', '')} {person.get('idNoMasked', '')}")
        if block.get("costMasked"):
            lines.append("金额 ¥****")
    payload = remember_binary("穿透报告.pdf", _pdf(lines), "application/pdf", "asset_forward", expires_seconds=300)
    site_message(viewer_id(), "穿透报告已生成", "请到消息中心领取，链接 300 秒内有效", "/ims/workbench/messages", "ASSET_FORWARD", f"forward:{payload['id']}")
    return payload


def _pdf(lines: list[str]) -> bytes:
    import io

    from PIL import Image, ImageDraw, ImageFont

    font = _font(16)
    width = 720
    height = max(200, 36 + 28 * len(lines))
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        draw.text((24, 16 + index * 28), line, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PDF", resolution=144)
    return buffer.getvalue()


def _font(size: int):
    import os

    from PIL import ImageFont

    for path in (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()
