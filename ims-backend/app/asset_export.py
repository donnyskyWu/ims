"""ASSET 导出（#74 · E2E-S5-06）。

正向穿透报告为 PDF，反查结果为 xlsx。数据与穿透页同一套层级、入口和错误码。
回执下载挂在导出资源上（/export/file），文件同时落服务端目录 data/ims-files。
xlsx 复用 DC 已有的 UTF-8 表格生成。PDF 用 reportlab 嵌入中文字体，因为既有 Helvetica 生成器会丢掉非 ASCII。
"""

from __future__ import annotations

import os
import secrets
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.asset_penetrate import collect_reverse_export, forward_graph
from app.models import User

router = APIRouter()

EXPORT_TTL_SEC = 300
FORWARD_NAME = "asset_forward_report.pdf"
REVERSE_NAME = "asset_reverse_report.xlsx"
PDF_MEDIA = "application/pdf"
XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FORWARD_MESSAGE = "穿透报告已生成"
REVERSE_MESSAGE = "反查结果已生成"
DISK_FAIL = "报告生成失败，请稍后重试或联系管理员"
STATUS_LABEL = {
    "PENDING_REVIEW": "待审核",
    "IN_USE": "在用",
    "RETURNED": "已归还",
    "SCRAPPED": "已报废",
}
BIND_LABEL = {"HOLD": "持有", "GUARANTEE": "担保", "CUSTODY": "代管"}
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
)

# token -> (expires_at, body, media, filename, user_id, path)
_EXPORTS: dict[str, tuple[float, bytes, str, str, int, str]] = {}


def chain_lines(nodes: list[dict]) -> list[str]:
    lines = ["资产穿透报告"]
    for node in nodes:
        if node.get("layer") == "PERSON":
            prefix = "实名人"
        else:
            prefix = f"第{node.get('level') or 0}层"
        lines.append(f"{prefix} · {node.get('label') or ''}")
    return lines


def summary_text(summary: dict) -> str:
    return (
        f"命中 {summary.get('total') or 0} 条（在用 {summary.get('inUse') or 0} / "
        f"已归还 {summary.get('returned') or 0} / 已报废 {summary.get('scrapped') or 0}）"
    )


def reverse_matrix(items: list[dict], summary: dict) -> list[list[str]]:
    rows = [
        ["汇总", summary_text(summary)],
        ["资产编号", "名称", "状态", "绑定", "账号"],
    ]
    if not items:
        rows.append(["暂无绑定资产", "", "", "", ""])
    for item in items:
        status = STATUS_LABEL.get(item.get("status") or "", item.get("status") or "")
        bind = BIND_LABEL.get(item.get("bindType") or "", item.get("bindType") or "—")
        rows.append(
            [
                item.get("assetCode") or "",
                item.get("assetName") or "",
                status,
                bind or "—",
                item.get("relatedAccountNo") or "—",
            ]
        )
    return rows


def _register_cjk() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    if "IMS-CJK" in pdfmetrics.getRegisteredFontNames():
        return "IMS-CJK"
    for path in FONT_CANDIDATES:
        if not os.path.isfile(path):
            continue
        pdfmetrics.registerFont(TTFont("IMS-CJK", path, subfontIndex=0))
        return "IMS-CJK"
    raise FileNotFoundError("cjk font")


def build_pdf(lines: list[str]) -> bytes:
    from reportlab.pdfgen import canvas

    font = _register_cjk()
    buf = BytesIO()
    pdf = canvas.Canvas(buf, pagesize=(595, 842))
    pdf.setTitle("资产穿透报告")
    y = 800
    pdf.setFont(font, 12)
    for line in lines:
        if y < 48:
            pdf.showPage()
            pdf.setFont(font, 12)
            y = 800
        pdf.drawString(40, y, line[:80])
        y -= 18
    pdf.save()
    return buf.getvalue()


def build_xlsx(rows: list[list[str]]) -> bytes:
    from app.dc_trace import build_xlsx as dc_build_xlsx

    return dc_build_xlsx(rows)


def _root() -> Path:
    configured = (os.environ.get("IMS_FILE_ROOT") or "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "data" / "ims-files"


def purge_exports(now: float) -> None:
    dead = [key for key, item in _EXPORTS.items() if item[0] < now]
    for key in dead:
        path = _EXPORTS[key][5]
        _EXPORTS.pop(key, None)
        if path:
            Path(path).unlink(missing_ok=True)


def issue_export(
    actor_id: int,
    body: bytes,
    media: str,
    filename: str,
    kind: str,
    route: str | None = None,
    message: str | None = None,
) -> dict | None:
    now = time.time()
    purge_exports(now)
    token = secrets.token_urlsafe(24)
    ext = {"pdf": "pdf", "csv": "csv"}.get(kind, "xlsx")
    folder = _root() / "asset" / datetime.now().strftime("%Y%m")
    path = folder / f"{token}.{ext}"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    except OSError:
        return None
    _EXPORTS[token] = (now + EXPORT_TTL_SEC, body, media, filename, actor_id, str(path))
    route_name = route or ("forward" if kind == "pdf" else "reverse")
    text = message or (FORWARD_MESSAGE if kind == "pdf" else REVERSE_MESSAGE)
    return {
        "exportTaskId": token,
        "message": text,
        "downloadUrl": f"/admin-api/ims/asset/{route_name}/export/file?token={token}",
        "fileName": filename,
    }


def _file_response(token: str, actor: User):
    now = time.time()
    purge_exports(now)
    item = _EXPORTS.get(token)
    if item is None or item[0] < now:
        return fail(1002, "下载链接已过期")
    if item[4] != actor.id:
        return fail(1008, "无数据权限")
    _expires, body, media, filename, _user_id, _path = item
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/asset/forward/export/file")
def forward_export_file(token: str, actor: User = Depends(current_user)):
    return _file_response(token, actor)


@router.get("/asset/forward/export/{asset_id}")
def forward_export(
    asset_id: int,
    realnameId: int = 0,
    layers: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    graph, error = forward_graph(db, actor, asset_id, realnameId, layers)
    if error:
        return error
    nodes = graph.get("nodes") or []
    lines = chain_lines(nodes)
    empty = not any((node.get("layer") or "") != "PERSON" for node in nodes)
    if empty:
        lines.append("暂无资产层级")
    try:
        body = build_pdf(lines)
    except Exception:
        return fail(5005, DISK_FAIL)
    payload = issue_export(actor.id, body, PDF_MEDIA, FORWARD_NAME, "pdf")
    if payload is None:
        return fail(5005, DISK_FAIL)
    payload["empty"] = empty
    return ok(payload)


@router.get("/asset/reverse/export/file")
def reverse_export_file(token: str, actor: User = Depends(current_user)):
    return _file_response(token, actor)


@router.get("/asset/reverse/export")
def reverse_export(
    entryType: str,
    entryId: int = 0,
    accountNo: str = "",
    sessionCode: str = "",
    includeHistory: bool = True,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    payload, error = collect_reverse_export(
        db,
        actor,
        entryType,
        entryId,
        accountNo,
        sessionCode,
        include_history=includeHistory,
    )
    if error:
        return error
    try:
        body = build_xlsx(reverse_matrix(payload["items"], payload["summary"]))
    except Exception:
        return fail(5005, DISK_FAIL)
    issued = issue_export(actor.id, body, XLSX_MEDIA, REVERSE_NAME, "xlsx")
    if issued is None:
        return fail(5005, DISK_FAIL)
    issued["empty"] = not payload["items"]
    issued["summary"] = payload["summary"]
    return ok(issued)
