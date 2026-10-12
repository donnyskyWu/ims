"""引用登记。不建物理外键。"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import BigInteger
from sqlalchemy.orm import MappedColumn

REF_POLICIES = {"RESTRICT", "CASCADE_SOFT", "SET_NULL"}


@dataclass
class RefSpec:
    target: str
    on_delete: str = "RESTRICT"
    allow_disabled: bool = False
    external: bool = False
    enforce_delete: bool = True
    entity_label: str = ""


@dataclass
class NotARef:
    reason: str = ""


REGISTRY: dict[tuple[str, str], RefSpec] = {}


def Ref(target: str, on_delete: str = "RESTRICT", allow_disabled: bool = False, external: bool = False, enforce_delete: bool = True):
    if on_delete not in REF_POLICIES:
        raise ValueError(f"删除策略无效: {on_delete}")
    return RefSpec(target, on_delete, allow_disabled, external, enforce_delete)


def register_model_refs(model) -> None:
    table = model.__tablename__
    for column in model.__table__.columns:
        spec = column.info.get("ref")
        marker = column.info.get("not_a_ref")
        if spec is None and marker is None:
            continue
        if isinstance(spec, RefSpec):
            if not spec.on_delete:
                continue
            label = spec.entity_label
            REGISTRY[(table, column.name)] = spec
            if label:
                spec.entity_label = label


def validate_refs(models) -> list[str]:
    problems = []
    REGISTRY.clear()
    labels = {}
    for model in models:
        labels[model.__tablename__] = getattr(model, "__entity_label__", model.__tablename__)
        register_model_refs(model)
    for (table, column), spec in list(REGISTRY.items()):
        if not spec.entity_label:
            spec.entity_label = labels.get(spec.target, spec.target)
        if spec.on_delete not in REF_POLICIES:
            problems.append(f"{table}.{column} 缺少合法删除策略")
    skip_names = {"id", "tenant_id", "creator", "updater"}
    for model in models:
        if getattr(model, "__audit_exempt__", None) == "log":
            continue
        for column in model.__table__.columns:
            if not column.name.endswith("_id"):
                continue
            if column.name in skip_names:
                continue
            if not isinstance(column.type, BigInteger):
                continue
            if column.info.get("ref") is None and column.info.get("not_a_ref") is None:
                problems.append(f"{model.__name__}.{column.name} 未声明引用或例外")
            spec = column.info.get("ref")
            if isinstance(spec, RefSpec) and not spec.on_delete:
                problems.append(f"{model.__name__}.{column.name} 引用缺少删除策略")
    return problems


def refs_to(target_table: str, policy: str | None = None):
    found = []
    for (table, column), spec in REGISTRY.items():
        if spec.target != target_table or spec.external:
            continue
        if policy and spec.on_delete != policy:
            continue
        if policy is None and not spec.enforce_delete:
            continue
        found.append((table, column, spec))
    return found
