"""内容文案第三方客户端（IMS_CONTENT_AI_STUB）。

与 Football / collector 客户端同一风格：环境开关决定桩或 HTTP，基址来自系统参数，
请求体不能改写调用地址。

- ``success``（默认）：本地 Markdown，不访问外网
- ``fail``：返回失败，供界面重试
- ``http``：``POST {content.ai.baseUrl}/v1/chat/completions``（OpenAI 兼容）

``IMS_CONTENT_AI_STUB`` 为空且配置了 ``content.ai.baseUrl``（环境变量
``IMS_CONTENT_AI_BASE_URL``）时走 http。文案生成不写版式、不调用排版。
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from app.settings_runtime import get_param

CHAT_PATH = "/v1/chat/completions"
DEFAULT_TIMEOUT = float(os.environ.get("IMS_CONTENT_AI_TIMEOUT", "30") or "30")

STUB_MODELS: tuple[dict[str, str], ...] = (
    {"id": "stub-qwen", "modelName": "qwen-plus", "vendor": "STUB", "status": "ENABLED"},
    {"id": "stub-gpt", "modelName": "gpt-4o-mini", "vendor": "STUB", "status": "ENABLED"},
)


def base_url() -> str:
    return get_param("content.ai.baseUrl").strip().rstrip("/")


def stub_mode() -> str:
    explicit = (os.environ.get("IMS_CONTENT_AI_STUB") or "").strip().lower()
    if explicit:
        return explicit
    if base_url():
        return "http"
    return "success"


def stub_models() -> list[dict[str, str]]:
    return [dict(row) for row in STUB_MODELS]


def render_stub(
    *,
    prompt: str,
    model_name: str,
    round_count: int,
    current_body: str,
) -> str:
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


def generate_copy(
    *,
    model_name: str,
    prompt: str,
    round_count: int,
    current_body: str,
    history: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str | None]:
    """成功返回 ({markdown, mock}, None)；失败返回 (None, reason)。"""
    mode = stub_mode()
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
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None, "AI 文案生成失败"
    text = extract_markdown(data)
    if not text:
        return None, "AI 文案生成失败"
    return {"markdown": text, "mock": False}, None
