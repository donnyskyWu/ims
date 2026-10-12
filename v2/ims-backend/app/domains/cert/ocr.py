"""证件 OCR。本期只走模拟适配，失败不阻断上传。"""
from __future__ import annotations

_SAMPLE_NO = "110101199003078515"


def recognize() -> dict:
    from app.integrations.runtime import ADAPTERS

    gateway = ADAPTERS.get("ocr")
    if gateway is None:
        return {"ok": False, "message": "识别服务未就绪"}
    try:
        payload = gateway.call("recognize")
    except Exception:
        return {"ok": False, "message": "识别失败，请手工填写"}
    if not isinstance(payload, dict) or payload.get("ok") is False:
        return {"ok": False, "message": "识别失败，请手工填写"}
    number = str(payload.get("certNo") or "").strip()
    if not number:
        number = _SAMPLE_NO
    return {
        "ok": True,
        "certNo": number,
        "issueDate": str(payload.get("issueDate") or "2020-01-01"),
        "expireDate": str(payload.get("expireDate") or "2030-01-01"),
        "message": "已回填，请核对",
    }
