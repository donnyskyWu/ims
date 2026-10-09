"""主数据 MASTER · 台账汇总（W9-13）。"""

from __future__ import annotations

from datetime import timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, ok
from app.core import utcnow
from app.corp import ops_db, tenant_of
from app.models import CertArchive, User
from app.ops_models import Company, Phone, PlatformAccount, Realname, SimCard

router = APIRouter(tags=["master"])


@router.get("/master/overview")
def master_overview(
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)

    def ims_count(model) -> int:
        return int(
            db.scalar(select(func.count()).select_from(model).where(model.deleted == 0, model.tenant_id == tenant_id))
            or 0
        )

    def ops_count(model) -> int:
        return int(
            ops.scalar(select(func.count()).select_from(model).where(model.deleted == 0, model.tenant_id == tenant_id))
            or 0
        )

    blocks = [
        {"key": "company", "label": "公司主体", "count": ops_count(Company), "href": "/ims/corp/resource/company"},
        {"key": "realname", "label": "实名人", "count": ops_count(Realname), "href": "/ims/corp/resource/realname"},
        {"key": "sim", "label": "SIM 卡", "count": ops_count(SimCard), "href": "/ims/corp/resource/sim-card"},
        {"key": "certificate", "label": "证件档案", "count": ims_count(CertArchive), "href": "/ims/corp/resource/certificate"},
        {"key": "phone", "label": "工作手机", "count": ops_count(Phone), "href": "/ims/corp/device/phone"},
        {"key": "platformAccount", "label": "平台账号", "count": ops_count(PlatformAccount), "href": "/ims/corp/account/douyin"},
    ]
    stamp = utcnow().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8)))
    return ok({"blocks": blocks, "updatedAt": stamp.strftime("%Y-%m-%d %H:%M:%S")})
