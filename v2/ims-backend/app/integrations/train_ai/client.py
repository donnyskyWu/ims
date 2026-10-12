"""培训出题。连接参数只从系统参数读取，调用日志不记录密钥。"""
from __future__ import annotations

import json
import time

from sqlalchemy import select

from app.core.context import get_ctx
from app.core.errors import BizError
from app.db.session import session_scope
from app.domains.system.model import Param, TrainAiCallLog

PARAM_KEYS = (
    "train_ai.enabled",
    "train_ai.mode",
    "train_ai.api_key",
    "train_ai.base_url",
    "train_ai.model",
    "train_ai.timeout_ms",
    "train_ai.max_questions",
)

mock_questions: list[dict] = []

_SINGLE = {"SINGLE", "SINGLE_CHOICE"}
_JUDGE = {"JUDGE", "TRUE_FALSE", "BOOLEAN"}


def load_params(loader=None) -> dict:
    if loader is not None:
        return {str(key): value for key, value in dict(loader() if callable(loader) else loader).items()}
    with session_scope() as session:
        rows = session.scalars(select(Param).where(Param.param_key.in_(PARAM_KEYS))).all()
        return {row.param_key: row.value for row in rows}


def _enabled(params: dict) -> bool:
    return str(params.get("train_ai.enabled") or "").strip().lower() in {"1", "true", "yes", "on"}


def _has_answer(item) -> bool:
    if not isinstance(item, dict):
        return False
    if "answer" in item and item.get("answer") not in (None, ""):
        return True
    if item.get("answerIndex") is not None:
        return True
    if item.get("answerBoolean") is not None:
        return True
    return False


def _limit(params: dict) -> int:
    try:
        value = int(params.get("train_ai.max_questions") or 20)
    except (TypeError, ValueError):
        return 20
    return value if value > 0 else 20


def _select_questions(raw, single_count: int, judge_count: int, limit: int) -> list[dict]:
    valid = [item for item in list(raw or []) if _has_answer(item)]
    singles, judges, others = [], [], []
    for item in valid:
        kind = str(item.get("type") or item.get("questionType") or "").upper()
        if kind in _SINGLE:
            singles.append(item)
        elif kind in _JUDGE:
            judges.append(item)
        else:
            others.append(item)
    need_single = max(0, int(single_count))
    need_judge = max(0, int(judge_count))
    chosen = singles[:need_single] + judges[:need_judge]
    need = need_single + need_judge
    if len(chosen) < need:
        for item in others:
            if len(chosen) >= need:
                break
            chosen.append(item)
    if not chosen and valid and need > 0:
        chosen = valid[:need]
    return chosen[:limit]


def _parse_questions(content: str):
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if "```" in text:
            text = text.rsplit("```", 1)[0]
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("questions") or data.get("data") or []
    if not isinstance(data, list):
        raise RuntimeError("题目格式不正确")
    return data


def _call_real(params: dict, single_count: int, judge_count: int):
    import httpx

    key = str(params.get("train_ai.api_key") or "").strip()
    base = str(params.get("train_ai.base_url") or "").strip().rstrip("/")
    model = str(params.get("train_ai.model") or "")
    timeout_ms = int(params.get("train_ai.timeout_ms") or 60000)
    url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "只返回 JSON，对象含 questions 数组，每题必须有 answer。"},
            {
                "role": "user",
                "content": json.dumps(
                    {"single": int(single_count), "judge": int(judge_count)},
                    ensure_ascii=False,
                ),
            },
        ],
    }
    headers = {"Authorization": f"Bearer {key}"}
    timeout = httpx.Timeout(timeout_ms / 1000)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=payload, headers=headers)
    if response.status_code >= 400:
        raise RuntimeError("call fail")
    body = response.json()
    content = body["choices"][0]["message"]["content"]
    return _parse_questions(content)


def _log(material_id, question_count: int, cost_ms: int, result_code: int) -> None:
    ctx = get_ctx()
    operator = ctx.user_id if ctx and ctx.user_id is not None else None
    with session_scope(commit=True) as session:
        session.add(
            TrainAiCallLog(
                operator_id=operator,
                material_id=material_id,
                question_count=int(question_count),
                cost_ms=max(0, int(cost_ms)),
                result_code=int(result_code),
            )
        )


def _fail(material_id, started: float, code: int):
    cost = int((time.perf_counter() - started) * 1000)
    _log(material_id, 0, cost, code)
    raise BizError(code)


def generate_quiz(material_published, single_count, judge_count, material_id=None, loader=None):
    started = time.perf_counter()
    if not material_published:
        _fail(material_id, started, 1101)
    params = load_params(loader)
    if not _enabled(params):
        _fail(material_id, started, 1109)
    mode = str(params.get("train_ai.mode") or "").strip().lower()
    if mode == "real":
        key = str(params.get("train_ai.api_key") or "").strip()
        base = str(params.get("train_ai.base_url") or "").strip()
        if not key or not base:
            _fail(material_id, started, 1109)
        try:
            raw = _call_real(params, single_count, judge_count)
        except Exception as exc:
            import httpx

            code = 1107 if isinstance(exc, httpx.TimeoutException) else 1106
            _fail(material_id, started, code)
    elif mode == "mock":
        raw = list(mock_questions)
    else:
        _fail(material_id, started, 1109)
    chosen = _select_questions(raw, single_count, judge_count, _limit(params))
    if not chosen:
        _fail(material_id, started, 1108)
    cost = int((time.perf_counter() - started) * 1000)
    _log(material_id, len(chosen), cost, 0)
    return chosen
