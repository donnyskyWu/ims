"""ComfyUI HTTP 客户端（V1-C1：只走 HTTP API，不操作 ComfyUI 前端）。

- `POST /prompt` 提交
- `GET  /history/{prompt_id}` 查询

鉴权 `Authorization: Bearer <token>`（可选）。地址 `comfyui.baseUrl` / `IMS_COMFYUI_BASE_URL`，
Token `comfyui.tokenSecret` / `IMS_COMFYUI_TOKEN`。

桩：`IMS_COMFYUI_STUB=1`（成功）/`fail` / `timeout`，或统一 `IMS_CONTENT_GEN_STUB`。
桩不占用本机 GPU，产物键固定为 `stub/comfyui/stable-demo.mp4`。
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from app.settings_runtime import get_param

PROMPT_PATH = "/prompt"
HISTORY_PATH = "/history/{prompt_id}"
STUB_FILE_KEY = "stub/comfyui/stable-demo.mp4"

MSG_TIMEOUT = "视频生成超时，可重新发起"
MSG_UNCONFIGURED = "未配置 ComfyUI 地址（comfyui.baseUrl / IMS_COMFYUI_BASE_URL）"
MSG_UNREACHABLE = "无法连接 ComfyUI，可重新发起"
MSG_DENIED = "ComfyUI 拒绝访问，请管理员核对 Token 配置"
MSG_QUEUE = "ComfyUI 队列满或 GPU 不可用"
MSG_FAIL = "视频生成失败，可重新发起"
MSG_PARAMS = "params 不符合工作流"

_lock = threading.Lock()
_seq = 0
_jobs: dict[str, dict] = {}


@dataclass
class VideoJob:
    ok: bool
    code: int | None
    message: str
    upstream_id: str = ""
    status: str = ""
    file_key: str = ""
    progress: int | None = None
    retryable: bool = False
    http_status: int = 0


def _flag(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return None
    return str(raw).strip().lower()


def stub_mode() -> str:
    specific = _flag("IMS_COMFYUI_STUB")
    unified = _flag("IMS_CONTENT_GEN_STUB")
    chosen = specific if specific is not None else unified
    if chosen is None or chosen in ("0", "false", "no", "off"):
        return "off"
    if chosen in ("fail", "timeout"):
        return chosen
    if chosen in ("1", "true", "yes", "on", "success"):
        return "success"
    return "off"


def provider_name() -> str:
    """stub | remote | unconfigured。不回传地址或 Token。"""
    if stub_mode() != "off":
        return "stub"
    if base_url():
        return "remote"
    return "unconfigured"


def base_url() -> str:
    return get_param("comfyui.baseUrl").strip().rstrip("/")


def token() -> str:
    return get_param("comfyui.tokenSecret").strip()


def timeout_sec() -> float:
    raw = (os.environ.get("IMS_COMFYUI_TIMEOUT") or "").strip()
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


def _queue_full(message: str, code: int | None, http_status: int) -> bool:
    text = (message or "").lower()
    if http_status in (429, 503) or code == 5004:
        return True
    if "queue" in text or "gpu" in text or "队列" in (message or "") or "不可用" in (message or ""):
        return True
    return False


def _map_http(response: httpx.Response, body: dict) -> VideoJob | None:
    message = str(body.get("message") or body.get("msg") or body.get("error") or "")
    if isinstance(body.get("node_errors"), dict) and body["node_errors"]:
        return VideoJob(False, 1001, MSG_PARAMS, status="FAILED", retryable=False, http_status=response.status_code)
    code = body.get("code")
    code_int = code if isinstance(code, int) else None
    if response.status_code in (401, 403) or code_int in (401, 403):
        return VideoJob(False, 1001, MSG_DENIED, status="FAILED", retryable=True, http_status=response.status_code)
    if code_int == 1056 or "超时" in message or "timeout" in message.lower():
        return VideoJob(False, 1056, MSG_TIMEOUT, status="FAILED", retryable=True, http_status=response.status_code)
    if _queue_full(message, code_int, response.status_code):
        return VideoJob(False, 5004, MSG_QUEUE, status="FAILED", retryable=True, http_status=response.status_code)
    if response.status_code >= 400 or (code_int not in (None, 0)):
        msg = message or f"视频生成失败（HTTP {response.status_code}），可重新发起"
        ims = 1001
        if code_int in (1001, 1056, 5004):
            ims = code_int
        return VideoJob(False, ims, msg[:200], status="FAILED", retryable=True, http_status=response.status_code)
    return None


def _file_key_from_outputs(outputs: dict) -> str:
    if not isinstance(outputs, dict):
        return ""
    for node in outputs.values():
        if not isinstance(node, dict):
            continue
        for key in ("videos", "gifs", "images"):
            items = node.get(key)
            if not isinstance(items, list) or not items:
                continue
            item = items[0]
            if isinstance(item, dict) and item.get("filename"):
                sub = str(item.get("subfolder") or "").strip("/")
                name = str(item["filename"])
                return f"{sub}/{name}" if sub else name
    return ""


def _stub_submit() -> VideoJob:
    mode = stub_mode()
    global _seq
    with _lock:
        _seq += 1
        upstream_id = f"stub-video-{_seq:04d}"
        if mode == "fail":
            _jobs[upstream_id] = {"status": "FAILED", "file_key": ""}
            return VideoJob(False, 5004, MSG_QUEUE, upstream_id, "FAILED", retryable=True)
        if mode == "timeout":
            _jobs[upstream_id] = {"status": "FAILED", "file_key": ""}
            return VideoJob(False, 1056, MSG_TIMEOUT, upstream_id, "FAILED", retryable=True)
        _jobs[upstream_id] = {"status": "WAITING", "file_key": STUB_FILE_KEY}
    return VideoJob(True, None, "ok", upstream_id, "WAITING", progress=0)


def _stub_status(upstream_id: str) -> VideoJob:
    with _lock:
        row = _jobs.get(upstream_id)
        if row is None:
            return VideoJob(False, 1001, "视频任务不存在", upstream_id, "FAILED")
        status = row["status"]
        if status == "WAITING":
            row["status"] = "GENERATING"
            return VideoJob(True, None, "ok", upstream_id, "GENERATING", progress=40)
        if status == "GENERATING":
            row["status"] = "SUCCESS"
            return VideoJob(True, None, "ok", upstream_id, "SUCCESS", file_key=row["file_key"], progress=100)
        if status == "SUCCESS":
            return VideoJob(True, None, "ok", upstream_id, "SUCCESS", file_key=row["file_key"] or STUB_FILE_KEY, progress=100)
        message = MSG_TIMEOUT if stub_mode() == "timeout" else MSG_FAIL
        code = 1056 if "超时" in message else 5004
        return VideoJob(False, code, message, upstream_id, "FAILED", retryable=True)


def submit_prompt(params: dict | None) -> VideoJob:
    mode = stub_mode()
    if mode != "off":
        return _stub_submit()
    root = base_url()
    if not root:
        return VideoJob(False, 5004, MSG_UNCONFIGURED, status="FAILED", retryable=False)
    graph = None
    if isinstance(params, dict):
        graph = params.get("graph") or params.get("prompt")
    if not isinstance(graph, dict):
        text = ""
        if isinstance(params, dict):
            text = str(params.get("text") or params.get("promptText") or "")
        graph = {
            "ims_text": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": text},
            }
        }
    try:
        with httpx.Client(timeout=timeout_sec()) as client:
            response = client.post(f"{root}{PROMPT_PATH}", headers=_headers(), json={"prompt": graph, "client_id": "ims-content"})
    except httpx.TimeoutException:
        return VideoJob(False, 1056, MSG_TIMEOUT, status="FAILED", retryable=True)
    except httpx.HTTPError:
        return VideoJob(False, 5004, MSG_UNREACHABLE, status="FAILED", retryable=True)
    payload = _read_body(response)
    mapped = _map_http(response, payload)
    if mapped is not None:
        return mapped
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    upstream_id = str(data.get("prompt_id") or data.get("promptId") or data.get("id") or "")
    if not upstream_id:
        return VideoJob(False, 1001, MSG_PARAMS, status="FAILED", retryable=False, http_status=response.status_code)
    return VideoJob(True, None, "ok", upstream_id, "WAITING", progress=0, http_status=response.status_code)


def prompt_status(upstream_id: str) -> VideoJob:
    mode = stub_mode()
    if mode != "off":
        return _stub_status(upstream_id)
    root = base_url()
    if not root:
        return VideoJob(False, 5004, MSG_UNCONFIGURED, upstream_id, "FAILED", retryable=False)
    path = HISTORY_PATH.format(prompt_id=quote(upstream_id, safe=""))
    try:
        with httpx.Client(timeout=timeout_sec()) as client:
            response = client.get(f"{root}{path}", headers=_headers())
    except httpx.TimeoutException:
        return VideoJob(False, 1056, MSG_TIMEOUT, upstream_id, "FAILED", retryable=True)
    except httpx.HTTPError:
        return VideoJob(False, 5004, MSG_UNREACHABLE, upstream_id, "FAILED", retryable=True)
    payload = _read_body(response)
    mapped = _map_http(response, payload)
    if mapped is not None:
        mapped.upstream_id = upstream_id
        return mapped
    entry = payload.get(upstream_id) if isinstance(payload.get(upstream_id), dict) else None
    if entry is None and isinstance(payload.get("data"), dict):
        entry = payload["data"]
    if not isinstance(entry, dict) or not entry:
        return VideoJob(True, None, "ok", upstream_id, "GENERATING", progress=30, http_status=response.status_code)
    status_obj = entry.get("status") if isinstance(entry.get("status"), dict) else {}
    status_str = str(status_obj.get("status_str") or status_obj.get("status") or "").lower()
    completed = bool(status_obj.get("completed"))
    if status_str in ("error", "failed"):
        return VideoJob(False, 1001, MSG_FAIL, upstream_id, "FAILED", retryable=True, http_status=response.status_code)
    file_key = _file_key_from_outputs(entry.get("outputs") if isinstance(entry.get("outputs"), dict) else {})
    if completed or status_str == "success" or file_key:
        return VideoJob(
            True,
            None,
            "ok",
            upstream_id,
            "SUCCESS",
            file_key or STUB_FILE_KEY,
            100,
            http_status=response.status_code,
        )
    return VideoJob(True, None, "ok", upstream_id, "GENERATING", progress=50, http_status=response.status_code)


def reset_stub() -> None:
    global _seq
    with _lock:
        _seq = 0
        _jobs.clear()
