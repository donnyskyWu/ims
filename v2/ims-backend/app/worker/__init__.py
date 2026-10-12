"""Worker 与 API 共用模型，不注册 HTTP 路由。"""
from __future__ import annotations

ROUTES: list = []


def registered_jobs():
    import app.services.jobs as jobs

    return list(jobs.JOBS)


def model_classes():
    from app.domains import all_models

    return all_models()
