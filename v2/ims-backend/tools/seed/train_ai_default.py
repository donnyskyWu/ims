"""培训 AI 联调占位。不写入 ims_sys_param，运行时不读取。

正式模型和提示词配置在 B10。这里只补缺，不覆盖已有值。密钥留空。
"""

PLACEHOLDER = {
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "qwen3.8-max",
    "api_key": "",
    "mode": "mock",
    "timeout_ms": 60000,
    "max_questions": 20,
}


def fill_missing(current: dict | None) -> dict:
    merged = dict(current or {})
    for key, value in PLACEHOLDER.items():
        if merged.get(key) in (None, ""):
            merged[key] = value
    return merged
