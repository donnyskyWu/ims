"""内容文案第三方 HTTP 客户端（对齐 Collector：地址 + Token，桩可切换）。

预留路径（真实服务按此实现，IMS 不写死密钥）：

- `POST /v1/copy/jobs` 提交
- `GET  /v1/copy/jobs/{id}` 查询

鉴权 `Authorization: Bearer <token>`。地址 `content.ai.baseUrl` / `IMS_CONTENT_AI_BASE_URL`，
Token `content.ai.tokenSecret` / `IMS_CONTENT_AI_TOKEN`（系统参数掩码，响应不回显）。

桩：`IMS_CONTENT_AI_STUB=1`（成功）/`fail` / `timeout`，或统一 `IMS_CONTENT_GEN_STUB`。
桩优先于真实地址，返回稳定假文案。
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.settings_runtime import get_param

SUBMIT_PATH = "/v1/copy/jobs"
STATUS_PATH = "/v1/copy/jobs/{job_id}"
CHAT_PATH = "/v1/chat/completions"
STUB_MODELS: tuple[dict[str, str], ...] = (
    {"id": "stub-qwen", "modelName": "qwen-plus", "vendor": "STUB", "status": "ENABLED"},
    {"id": "stub-gpt", "modelName": "gpt-4o-mini", "vendor": "STUB", "status": "ENABLED"},
)

STUB_COPY_V1 = (
    "【桩】口播稿 v1\n"
    "开场：今晚这场，先看节奏再看细节。\n"
    "中段：主队控球占优，客队反击看边路。\n"
    "结尾：理性看球，理性互动。"
)
STUB_COPY_V2 = (
    "【桩】口播稿 v2\n"
    "开场：三分钟讲清这场怎么看。\n"
    "中段：关键球员状态与历史交锋。\n"
    "结尾：评论区见。"
)
STUB_COPY_V3 = (
    "【桩】口播稿 v3\n"
    "开场：只讲一个看点。\n"
    "中段：定位球与临场调整。\n"
    "结尾：下期再见。"
)
STUB_COPIES = (STUB_COPY_V1, STUB_COPY_V2, STUB_COPY_V3)

MSG_TIMEOUT = "AI 文案生成超时，可重新发起"
MSG_UNCONFIGURED = "未配置 AI 文案地址（content.ai.baseUrl / IMS_CONTENT_AI_BASE_URL）"
MSG_UNREACHABLE = "无法连接文案服务，可重新发起"
MSG_DENIED = "文案服务拒绝访问，请管理员核对 Token 配置"
MSG_FAIL = "文案生成失败，可重新发起"

_lock = threading.Lock()
_seq = 0
_jobs: dict[str, dict] = {}


@dataclass
class CopyJob:
    ok: bool
    code: int | None
    message: str
    upstream_id: str = ""
    status: str = ""
    copies: list[str] = field(default_factory=list)
    retryable: bool = False
    http_status: int = 0


def _flag(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return None
    return str(raw).strip().lower()


def copy_provider_name() -> str:
    """stub | remote | unconfigured。不回传地址或 Token。"""
    mode = _draft_copy_mode()
    if mode == "http":
        return "remote" if base_url() else "unconfigured"
    return "stub"


def stub_mode() -> str:
    """off | success | fail | timeout。具体开关优先于 IMS_CONTENT_GEN_STUB。"""
    specific = _flag("IMS_CONTENT_AI_STUB")
    unified = _flag("IMS_CONTENT_GEN_STUB")
    chosen = specific if specific is not None else unified
    if chosen is None or chosen in ("0", "false", "no", "off"):
        return "off"
    if chosen in ("fail", "timeout"):
        return chosen
    if chosen in ("1", "true", "yes", "on", "success"):
        return "success"
    return "off"


def base_url() -> str:
    return get_param("content.ai.baseUrl").strip().rstrip("/")


def token() -> str:
    return get_param("content.ai.tokenSecret").strip()


def timeout_sec() -> float:
    raw = (os.environ.get("IMS_CONTENT_AI_TIMEOUT") or "").strip()
    try:
        value = float(raw) if raw else 20.0
    except ValueError:
        value = 20.0
    return value if value > 0 else 20.0


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    secret = token()
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    return headers


def _read_body(response: httpx.Response) -> dict:
    try:
        data = response.json()
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _copies_for(count: int) -> list[str]:
    n = 2 if count < 2 else 3 if count > 3 else count
    return list(STUB_COPIES[:n])


def _map_http(response: httpx.Response, body: dict) -> CopyJob | None:
    message = str(body.get("message") or body.get("msg") or body.get("error") or "")
    code = body.get("code")
    code_int = code if isinstance(code, int) else None
    text = message.lower()
    if response.status_code in (401, 403) or code_int in (401, 403):
        return CopyJob(False, 1001, MSG_DENIED, status="FAILED", retryable=True, http_status=response.status_code)
    if code_int == 1056 or "超时" in message or "timeout" in text:
        return CopyJob(False, 1056, MSG_TIMEOUT, status="FAILED", retryable=True, http_status=response.status_code)
    if response.status_code in (429, 503) or code_int == 5004 or "queue" in text or "gpu" in text or "队列" in message:
        return CopyJob(
            False,
            5004,
            "文案服务繁忙，可重新发起",
            status="FAILED",
            retryable=True,
            http_status=response.status_code,
        )
    if response.status_code >= 400 or (code_int not in (None, 0)):
        msg = message or f"文案生成失败（HTTP {response.status_code}），可重新发起"
        ims = 1001 if response.status_code < 500 and code_int not in (1056, 5004) else (code_int or 1001)
        if ims not in (1001, 1056, 5004):
            ims = 1001
        return CopyJob(False, ims, msg[:200], status="FAILED", retryable=True, http_status=response.status_code)
    return None


def _payload_data(body: dict) -> dict:
    data = body.get("data")
    if isinstance(data, dict):
        return data
    return body


def _status_of(data: dict) -> str:
    raw = str(data.get("status") or data.get("queueStatus") or "").upper()
    if raw in ("WAITING", "QUEUED", "PENDING"):
        return "WAITING"
    if raw in ("GENERATING", "RUNNING"):
        return "GENERATING"
    if raw in ("SUCCESS", "SUCCEEDED", "DONE"):
        return "SUCCESS"
    if raw in ("FAILED", "ERROR", "TIMEOUT"):
        return "FAILED"
    return raw or "WAITING"


def _copies_of(data: dict) -> list[str]:
    raw = data.get("copies") or data.get("candidates") or data.get("texts")
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    text = data.get("content") or data.get("text")
    if isinstance(text, str) and text.strip():
        return [text]
    return []


def _stub_submit(candidate_count: int) -> CopyJob:
    mode = stub_mode()
    global _seq
    with _lock:
        _seq += 1
        upstream_id = f"stub-copy-{_seq:04d}"
        if mode == "fail":
            _jobs[upstream_id] = {"status": "FAILED", "copies": [], "count": candidate_count}
            return CopyJob(False, 1001, MSG_FAIL, upstream_id, "FAILED", retryable=True)
        if mode == "timeout":
            _jobs[upstream_id] = {"status": "FAILED", "copies": [], "count": candidate_count}
            return CopyJob(False, 1056, MSG_TIMEOUT, upstream_id, "FAILED", retryable=True)
        _jobs[upstream_id] = {"status": "WAITING", "copies": _copies_for(candidate_count), "count": candidate_count}
    return CopyJob(True, None, "ok", upstream_id, "WAITING", retryable=False)


def _stub_status(upstream_id: str) -> CopyJob:
    with _lock:
        row = _jobs.get(upstream_id)
        if row is None:
            return CopyJob(False, 1001, "文案任务不存在", upstream_id, "FAILED", retryable=False)
        status = row["status"]
        if status == "WAITING":
            row["status"] = "GENERATING"
            return CopyJob(True, None, "ok", upstream_id, "GENERATING")
        if status == "GENERATING":
            row["status"] = "SUCCESS"
            return CopyJob(True, None, "ok", upstream_id, "SUCCESS", copies=list(row["copies"]))
        if status == "SUCCESS":
            return CopyJob(True, None, "ok", upstream_id, "SUCCESS", copies=list(row["copies"]))
        message = MSG_TIMEOUT if stub_mode() == "timeout" else MSG_FAIL
        code = 1056 if stub_mode() == "timeout" else 1001
        return CopyJob(False, code, message, upstream_id, "FAILED", retryable=True)


def submit_copy(*, requirement: str, script_type: str, candidate_count: int) -> CopyJob:
    mode = stub_mode()
    if mode != "off":
        return _stub_submit(candidate_count)
    root = base_url()
    if not root:
        return CopyJob(False, 1001, MSG_UNCONFIGURED, status="FAILED", retryable=False)
    url = f"{root}{SUBMIT_PATH}"
    body = {
        "requirement": requirement,
        "scriptType": script_type,
        "candidateCount": candidate_count,
    }
    try:
        with httpx.Client(timeout=timeout_sec()) as client:
            response = client.post(url, headers=_headers(), json=body)
    except httpx.TimeoutException:
        return CopyJob(False, 1056, MSG_TIMEOUT, status="FAILED", retryable=True)
    except httpx.HTTPError:
        return CopyJob(False, 1001, MSG_UNREACHABLE, status="FAILED", retryable=True)
    payload = _read_body(response)
    mapped = _map_http(response, payload)
    if mapped is not None:
        return mapped
    data = _payload_data(payload)
    upstream_id = str(data.get("id") or data.get("jobId") or "")
    status = _status_of(data)
    copies = _copies_of(data)
    return CopyJob(True, None, "ok", upstream_id, status, copies, http_status=response.status_code)


def copy_status(upstream_id: str) -> CopyJob:
    mode = stub_mode()
    if mode != "off":
        return _stub_status(upstream_id)
    root = base_url()
    if not root:
        return CopyJob(False, 1001, MSG_UNCONFIGURED, upstream_id, "FAILED", retryable=False)
    path = STATUS_PATH.format(job_id=upstream_id)
    try:
        with httpx.Client(timeout=timeout_sec()) as client:
            response = client.get(f"{root}{path}", headers=_headers())
    except httpx.TimeoutException:
        return CopyJob(False, 1056, MSG_TIMEOUT, upstream_id, "FAILED", retryable=True)
    except httpx.HTTPError:
        return CopyJob(False, 1001, MSG_UNREACHABLE, upstream_id, "FAILED", retryable=True)
    payload = _read_body(response)
    mapped = _map_http(response, payload)
    if mapped is not None:
        mapped.upstream_id = upstream_id
        return mapped
    data = _payload_data(payload)
    status = _status_of(data)
    copies = _copies_of(data)
    ok = status != "FAILED"
    code = None if ok else 1001
    message = "ok" if ok else MSG_FAIL
    return CopyJob(ok, code, message, upstream_id, status, copies, retryable=not ok, http_status=response.status_code)


def reset_stub() -> None:
    """测试隔离桩内存。"""
    global _seq
    with _lock:
        _seq = 0
        _jobs.clear()


def stub_models() -> list[dict[str, str]]:
    return [dict(row) for row in STUB_MODELS]


def render_stub(*, prompt: str, model_name: str, round_count: int, current_body: str) -> str:
    """确定性桩文案。续写保留上一轮正文，便于预览对比。"""
    title = "润色稿" if round_count >= 2 else "文案"
    lines = [f"# {title}", "", f"模型：{model_name}", ""]
    if round_count >= 2:
        previous = (current_body or "").strip()[:4000]
        if previous:
            lines.append(previous)
            lines.append("")
        lines.append("## 本次修改")
        lines.append((prompt or "请在现有正文上续写一段。").strip())
        lines.append("")
        lines.append("续写：在上文基础上补充赛后看点与互动收束。")
    else:
        lines.append(prompt.strip())
        lines.append("")
        lines.append("正文从提示展开，供编辑预览后采纳。本段为桩生成，不改版式。")
    return "\n".join(lines)


def _clip(text: str, limit: int = 4000) -> str:
    return (text or "").strip()[:limit]


def build_messages(prompt: str, round_count: int, current_body: str, history: list[dict[str, Any]]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": "你是内容编辑助手。只输出 Markdown 正文。不要输出版式 HTML，不要调用排版。",
        }
    ]
    for item in history[-6:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": _clip(content)})
    if round_count >= 2:
        revision = _clip(prompt) or "请在现有正文上续写一段。"
        current = _clip(current_body)
        user = f"【当前正文】\n{current}\n\n【本次修改要求】\n{revision}" if current else revision
        messages.append({"role": "user", "content": user})
    else:
        messages.append({"role": "user", "content": _clip(prompt)})
    return messages


def extract_markdown(data: Any) -> str:
    if isinstance(data, str):
        return data.strip()
    if not isinstance(data, dict):
        return ""
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"].strip()
    for key in ("markdown", "content", "text"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    inner = data.get("data")
    if inner is not None and inner is not data:
        return extract_markdown(inner)
    return ""


def _draft_copy_mode() -> str:
    """文案预览与确认草稿。``IMS_CONTENT_AI_STUB`` 优先于系统参数 ``content.ai.stubMode``。

    返回 ``fail`` / ``http`` / ``stub``。任务客户端的 ``stub_mode()`` 仍只看环境变量。
    """
    raw = (os.environ.get("IMS_CONTENT_AI_STUB") or "").strip().lower()
    if raw in ("fail", "http"):
        return raw
    if raw in ("1", "true", "yes", "on", "success", "timeout"):
        return "stub"
    if raw in ("0", "false", "no", "off"):
        return "http" if base_url() else "stub"
    configured = get_param("content.ai.stubMode").strip().lower()
    if configured in ("fail", "http"):
        return configured
    if configured == "success":
        return "stub"
    if stub_mode() == "fail":
        return "fail"
    if stub_mode() == "off" and base_url():
        return "http"
    return "stub"


def generate_copy(
    *,
    model_name: str,
    prompt: str,
    round_count: int,
    current_body: str,
    history: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str | None]:
    """成功返回 ({markdown, mock}, None)；失败返回 (None, reason)。

    任务桩（success/timeout/1）与未配置地址时走本地 Markdown。
    IMS_CONTENT_AI_STUB=http，或未开桩但已配置 content.ai.baseUrl，或系统参数 stubMode=http 时走 OpenAI 兼容接口。
    """
    mode = _draft_copy_mode()
    if mode == "fail":
        return None, "AI 文案生成失败"
    if mode == "http":
        return _http_generate(
            model_name=model_name,
            prompt=prompt,
            round_count=round_count,
            current_body=current_body,
            history=history,
        )
    markdown = render_stub(
        prompt=prompt,
        model_name=model_name,
        round_count=round_count,
        current_body=current_body,
    )
    return {"markdown": markdown, "mock": True}, None


def _http_generate(
    *,
    model_name: str,
    prompt: str,
    round_count: int,
    current_body: str,
    history: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str | None]:
    root = base_url()
    if not root:
        return None, "AI 文案服务未配置"
    url = f"{root}{CHAT_PATH}"
    payload = {
        "model": model_name,
        "messages": build_messages(prompt, round_count, current_body, history),
    }
    try:
        with httpx.Client(timeout=timeout_sec()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None, "AI 文案生成失败"
    text = extract_markdown(data)
    if not text:
        return None, "AI 文案生成失败"
    return {"markdown": text, "mock": False}, None
