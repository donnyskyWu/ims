from app.integrations.runtime import ADAPTERS

client = ADAPTERS["comfyui"]


def render():
    return client.call("render")
