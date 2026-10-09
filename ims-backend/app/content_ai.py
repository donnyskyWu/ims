"""内容文案生成：预览，不落库、不排版。

路径对齐 OPS ``/ai-content/generate`` 的 IMS 运行时前缀
``/admin-api/ims/content/ai-content/*``。采纳由编辑端写入 ``body``。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.content import tenant
from app.content_ai_client import generate_copy, stub_models
from app.content_production import load_project
from app.models import AirModelConfig, User

router = APIRouter(prefix="/content/ai-content", tags=["content-ai"])


class HistoryTurn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    role: str = ""
    content: str = ""


class GenerateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    modelId: str
    prompt: str = ""
    contentId: int | None = None
    roundCount: int = 1
    history: list[HistoryTurn] = Field(default_factory=list)
    currentBody: str = ""
    documentType: str = ""
    contentType: str = ""
    isPaywall: bool | None = None


def _catalog(db: Session, actor: User) -> list[dict[str, str]]:
    rows = stub_models()
    tid = tenant(actor)
    configured = db.scalars(
        select(AirModelConfig).where(
            AirModelConfig.deleted == 0,
            AirModelConfig.tenant_id == tid,
            AirModelConfig.status == "CONNECTED",
        )
    ).all()
    for row in configured:
        rows.append(
            {
                "id": str(row.id),
                "modelName": row.model_name,
                "vendor": row.vendor or "",
                "status": "ENABLED",
            }
        )
    return rows


def _model_name(catalog: list[dict[str, str]], model_id: str) -> str | None:
    for row in catalog:
        if row["id"] == model_id:
            return row["modelName"]
    return None


@router.get("/models")
def ai_models(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    return ok(_catalog(db, actor))


@router.post("/generate")
def ai_generate(
    body: GenerateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    model_id = (body.modelId or "").strip()
    prompt = (body.prompt or "").strip()
    if not model_id:
        return fail(1500, "参数校验失败")
    if body.roundCount < 1 or body.roundCount > 10:
        return fail(1500, "参数校验失败")
    if body.roundCount <= 1 and not prompt:
        return fail(1500, "参数校验失败")
    if body.roundCount >= 2 and not prompt and not (body.currentBody or "").strip():
        return fail(1500, "参数校验失败")
    if body.contentId:
        row = load_project(db, body.contentId, actor)
        if row is None:
            return fail(1504, "资源不可用")
    catalog = _catalog(db, actor)
    model_name = _model_name(catalog, model_id)
    if not model_name:
        return fail(1500, "模型不可用")
    history = [{"role": turn.role, "content": turn.content} for turn in body.history]
    generated, err = generate_copy(
        model_name=model_name,
        prompt=prompt,
        round_count=body.roundCount,
        current_body=body.currentBody or "",
        history=history,
    )
    if err or generated is None:
        return fail(1500, err or "AI 文案生成失败")
    # 预览不写 body / layout_html。仓库无 paid_body、free_body 列，采纳目标固定为 body。
    return ok(
        {
            "markdown": generated["markdown"],
            "mock": bool(generated["mock"]),
            "roundCount": body.roundCount,
            "modelId": model_id,
            "modelName": model_name,
            "targetField": "body",
            "layoutApplied": False,
            "documentType": (body.documentType or "")[:32],
            "isPaywall": body.isPaywall,
        }
    )
