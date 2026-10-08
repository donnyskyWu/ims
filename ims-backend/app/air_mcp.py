"""MCP 网关 POST /ims/mcp。本地组装，不调用外部大模型或供应商。

鉴权通过后按 Key 的 qpm_limit 做分钟窗限流。超限 HTTP 429，并写 ims_mcp_log
与站内通知（不进入预警中心）。
"""

from __future__ import annotations

import hashlib
import json
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.air_key import hash_key, key_blocked_reason, qpm_now, try_consume_qpm, window_start
from app.air_skill import skill_visible_to
from app.api import db_session
from app.core import utcnow
from app.models import AirApiKey, AirExpert, AirMcpLog, AirSkill, User

router = APIRouter(tags=["air-mcp"])

TOOL_NAMES = ("skills.list", "skills.get", "experts.list", "experts.assemble")


class McpCall(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    jsonrpc: str = "2.0"
    id: int | str | None = 1
    method: str
    params: dict | None = None


def presented_key(request: Request) -> str:
    authorization = request.headers.get("authorization") or ""
    if authorization:
        if authorization.lower().startswith("bearer "):
            return authorization[7:].strip()
        return ""
    return (request.query_params.get("key") or "").strip()


def rpc_ok(call_id: int | str | None, result: dict) -> JSONResponse:
    return JSONResponse(status_code=200, content={"jsonrpc": "2.0", "id": call_id, "result": result})


def rpc_error(status: int, call_id: int | str | None, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"jsonrpc": "2.0", "id": call_id, "error": {"code": code, "message": message}},
    )


def tool_defs() -> list[dict]:
    return [
        {
            "name": "skills.list",
            "description": "列出已发布技能（本地库，无模型调用）",
            "inputSchema": {"type": "object", "properties": {"keyword": {"type": "string"}}},
        },
        {
            "name": "skills.get",
            "description": "按编号读取已发布技能",
            "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
        },
        {
            "name": "experts.list",
            "description": "列出已发布专家包",
            "inputSchema": {"type": "object"},
        },
        {
            "name": "experts.assemble",
            "description": "组装提示词与技能引用，网关不执行模型",
            "inputSchema": {
                "type": "object",
                "properties": {"code": {"type": "string"}, "message": {"type": "string"}},
                "required": ["code"],
            },
        },
    ]


def run_tool(db: Session, key: AirApiKey, name: str, arguments: dict) -> tuple[dict | None, int, str | None]:
    tenant_id = key.tenant_id
    user_id = key.owner_user_id
    if name == "skills.list":
        rows = list(
            db.scalars(
                select(AirSkill).where(
                    AirSkill.deleted == 0,
                    AirSkill.tenant_id == tenant_id,
                    AirSkill.status == "PUBLISHED",
                )
            ).all()
        )
        keyword = str(arguments.get("keyword") or "").strip()
        category = str(arguments.get("category") or "").strip()
        items = []
        for row in rows:
            if not skill_visible_to(db, row, user_id):
                continue
            if category and row.category != category:
                continue
            if keyword and keyword not in row.skill_name and keyword not in row.skill_no:
                continue
            items.append(
                {"code": row.skill_no, "name": row.skill_name, "desc": row.category or "", "ver": row.version_label}
            )
        return {"items": items}, 200, None
    if name == "skills.get":
        code = str(arguments.get("code") or "").strip()
        row = db.scalar(
            select(AirSkill).where(
                AirSkill.deleted == 0,
                AirSkill.tenant_id == tenant_id,
                AirSkill.skill_no == code,
            )
        )
        if row is None or not skill_visible_to(db, row, user_id):
            return None, 403, "未授权"
        return (
            {"code": row.skill_no, "ver": row.version_label, "mdContent": "", "usageNote": row.skill_name},
            200,
            None,
        )
    if name == "experts.list":
        rows = list(
            db.scalars(
                select(AirExpert).where(
                    AirExpert.deleted == 0,
                    AirExpert.tenant_id == tenant_id,
                    AirExpert.status == "PUBLISHED",
                )
            ).all()
        )
        return {
            "items": [
                {
                    "code": row.expert_code,
                    "name": row.expert_name,
                    "scene": row.scene,
                    "ver": row.version_label,
                    "toolWhitelist": list(row.tool_whitelist or []),
                }
                for row in rows
            ]
        }, 200, None
    if name == "experts.assemble":
        code = str(arguments.get("code") or "").strip()
        row = db.scalar(
            select(AirExpert).where(
                AirExpert.deleted == 0,
                AirExpert.tenant_id == tenant_id,
                AirExpert.expert_code == code,
                AirExpert.status == "PUBLISHED",
            )
        )
        prompt = row.system_prompt if row is not None else ""
        return {
            "systemPrompt": prompt,
            "skillRefs": [],
            "guidelines": "网关只组装不下发模型执行",
        }, 200, None
    return None, 200, "未知工具"


def write_log(db: Session, key: AirApiKey, tool: str, params: dict | None, result_code: str, cost_ms: int) -> None:
    digest = hashlib.sha256(
        json.dumps(params or {}, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:32]
    db.add(
        AirMcpLog(
            key_id=key.id,
            user_id=key.owner_user_id,
            tool=tool[:64],
            param_digest=digest,
            result_code=result_code,
            cost_ms=cost_ms,
            tenant_id=key.tenant_id,
            created_at=utcnow(),
        )
    )
    db.flush()


def notify_qpm(db: Session, key: AirApiKey) -> None:
    from app.audit import publish_notify

    owner = db.get(User, key.owner_user_id)
    start = window_start()
    publish_notify(
        db,
        event_type="AIR_QPM_EXCEEDED",
        biz_key=f"key:{key.id}:{start.strftime('%Y%m%d%H%M')}",
        receiver=(owner.username if owner is not None else ""),
        receiver_user_id=key.owner_user_id,
        tenant_id=key.tenant_id or 0,
        creator=key.owner_user_id,
    )


@router.post("/ims/mcp")
def mcp_entry(request: Request, body: McpCall, db: Session = Depends(db_session)):
    plain = presented_key(request)
    if not plain:
        return rpc_error(401, body.id, 401, "缺少 API Key")
    key = db.scalar(
        select(AirApiKey).where(AirApiKey.deleted == 0, AirApiKey.key_hash == hash_key(plain))
    )
    if key is None:
        return rpc_error(401, body.id, 401, "Key 无效")
    blocked = key_blocked_reason(key)
    if blocked:
        return rpc_error(401, body.id, 401, f"Key 不可用：{blocked}")

    method = body.method.strip()
    params = body.params or {}
    if method == "initialize":
        return rpc_ok(
            body.id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ims-air", "version": "local"},
            },
        )
    if method in {"notifications/initialized", "ping"}:
        return rpc_ok(body.id, {})
    if method not in {"tools/list", "tools/call"}:
        return rpc_error(200, body.id, -32601, "不支持的方法")

    tool = "tools/list"
    arguments: dict = {}
    if method == "tools/call":
        tool = str(params.get("name") or "").strip()
        raw_args = params.get("arguments")
        arguments = raw_args if isinstance(raw_args, dict) else {}
        if tool not in TOOL_NAMES:
            if not try_consume_qpm(db, key):
                write_log(db, key, tool or "unknown", params, "429", 0)
                notify_qpm(db, key)
                key.last_used_at = qpm_now()
                return rpc_error(429, body.id, 429, "QPM 超限")
            write_log(db, key, tool or "unknown", params, "0", 0)
            key.last_used_at = qpm_now()
            return rpc_error(200, body.id, -32602, "未知工具")

    if not try_consume_qpm(db, key):
        write_log(db, key, tool, params, "429", 0)
        notify_qpm(db, key)
        key.last_used_at = qpm_now()
        return rpc_error(429, body.id, 429, "QPM 超限")

    started = time.perf_counter()
    if method == "tools/list":
        result = {"tools": tool_defs()}
    else:
        payload, http_status, error = run_tool(db, key, tool, arguments)
        if error:
            result_code = "403" if http_status == 403 else "0"
            write_log(db, key, tool, params, result_code, int((time.perf_counter() - started) * 1000))
            key.last_used_at = qpm_now()
            rpc_code = 403 if http_status == 403 else -32000
            return rpc_error(http_status, body.id, rpc_code, error)
        result = payload or {}
    write_log(db, key, tool, params, "0", int((time.perf_counter() - started) * 1000))
    key.last_used_at = qpm_now()
    return rpc_ok(body.id, result)
