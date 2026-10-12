from app.integrations.runtime import ADAPTERS

client = ADAPTERS["collector"]


def pull():
    return client.call("pull")
