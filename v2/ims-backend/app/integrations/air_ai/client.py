"""内容 AI。与培训 AI 分开，培训侧不得引用本模块。"""
from app.integrations.runtime import ADAPTERS

client = ADAPTERS["air_ai"]
CONFIG = {"base_url": "http://127.0.0.1:9/air", "model": "local-air"}


def current_config() -> dict:
    return dict(CONFIG)


def complete(prompt: str = ""):
    cfg = current_config()
    body = client.call("complete", {"prompt": prompt, "model": cfg.get("model")})
    if isinstance(body, dict):
        merged = dict(body)
        merged["model"] = cfg.get("model")
        merged["baseUrl"] = cfg.get("base_url")
        return merged
    return body
