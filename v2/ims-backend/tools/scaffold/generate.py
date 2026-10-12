"""按 YAML 定义生成模型、契约、服务、路由、页面和测试。"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

import yaml

from app.catalog import DICT_TYPE_NAMES
from app.core.clock import now_naive
from app.db.refs import REF_POLICIES

GENERATOR_VERSION = "1"
HEADER_MARKS = ("generator-version:", "def-hash:", "generated-at:")


class ScaffoldError(Exception):
    pass


def _snake(name: str) -> str:
    text = re.sub(r"(?<!^)(?=[A-Z])", "_", str(name or ""))
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return text or "entity"


def _pascal(name: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", str(name or "")) if part]
    if not parts:
        return "Entity"
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _hash_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def strip_headers(text: str) -> str:
    kept = [line for line in text.splitlines() if not any(mark in line for mark in HEADER_MARKS)]
    body = "\n".join(kept).strip()
    return body + "\n"


def body_hash(text: str) -> str:
    return _hash_bytes(strip_headers(text).encode("utf-8"))


def _headers(def_hash: str) -> str:
    stamp = now_naive().strftime("%Y-%m-%dT%H:%M:%S")
    return "\n".join(
        [
            f"# generator-version: {GENERATOR_VERSION}",
            f"# def-hash: {def_hash}",
            f"# generated-at: {stamp}",
        ]
    )


def _load(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    data = yaml.safe_load(raw.decode("utf-8")) or {}
    if not isinstance(data, dict):
        raise ScaffoldError("定义必须是对象")
    return data, _hash_bytes(raw)


def _validate(data: dict) -> None:
    table = str(data.get("table") or "")
    registry = data.get("registry") or []
    if isinstance(registry, str):
        registry = [registry]
    if table not in {str(item) for item in registry}:
        raise ScaffoldError(f"表未登记: {table}")
    perm = str(data.get("perm") or "")
    if not perm.startswith("ims"):
        raise ScaffoldError(f"权限码前缀必须是 ims: {perm}")
    for field in data.get("fields") or []:
        kind = str(field.get("type") or "string")
        if kind == "dict":
            dict_type = field.get("dict") or field.get("dict_type")
            if dict_type not in DICT_TYPE_NAMES:
                raise ScaffoldError(f"字典类型不存在: {dict_type}")
        if kind == "ref":
            policy = field.get("on_delete")
            if not policy:
                raise ScaffoldError(f"引用字段缺少删除策略: {field.get('name')}")
            if policy not in REF_POLICIES:
                raise ScaffoldError(f"删除策略无效: {field.get('name')}")


def _column(field: dict, table: str) -> str:
    name = field["name"]
    kind = str(field.get("type") or "string")
    if kind == "string":
        length = int(field.get("length") or 100)
        return f"    {name}: Mapped[str] = mapped_column(String({length}), nullable=False, default=\"\")"
    if kind == "text":
        return f"    {name}: Mapped[str | None] = mapped_column(Text, nullable=True)"
    if kind == "int":
        return f"    {name}: Mapped[int] = mapped_column(Integer, nullable=False, default=0)"
    if kind == "datetime":
        return f"    {name}: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)"
    if kind == "dict":
        dict_type = field.get("dict") or field.get("dict_type")
        return (
            f"    {name}: Mapped[str] = mapped_column(String(32), nullable=False, default=\"ENABLED\", "
            f"info={{\"dict\": \"{dict_type}\"}})"
        )
    if kind == "ref":
        target = str(field.get("target") or "")
        if target.lower() == "self":
            target = table
        policy = field["on_delete"]
        default = ", default=0" if name == "parent_id" else ""
        nullable = "False" if name == "parent_id" else "True"
        py = "int" if name == "parent_id" else "int | None"
        return (
            f"    {name}: Mapped[{py}] = mapped_column(BigInteger, nullable={nullable}{default}, "
            f"info={{\"ref\": Ref(\"{target}\", \"{policy}\")}})"
        )
    return f"    {name}: Mapped[str | None] = mapped_column(String(100), nullable=True)"


def _model(data: dict, header: str) -> str:
    table = data["table"]
    entity = _pascal(data.get("entity") or data.get("name") or table)
    label = data.get("label") or data.get("entity") or entity
    imports = ["BigInteger", "String"]
    body = []
    extra = set()
    for field in data.get("fields") or []:
        kind = str(field.get("type") or "string")
        if kind == "text":
            extra.add("Text")
        elif kind == "int":
            extra.add("Integer")
        elif kind == "datetime":
            extra.add("DateTime")
        body.append(_column(field, table))
    imports.extend(sorted(extra))
    lines = [
        header,
        '"""生成的模型。"""',
        "from __future__ import annotations",
        "",
    ]
    if "DateTime" in extra:
        lines.append("from datetime import datetime")
        lines.append("")
    lines.append("from sqlalchemy import " + ", ".join(imports))
    lines.append("from sqlalchemy.orm import Mapped, mapped_column")
    lines.append("")
    lines.append("from app.db.base import AuditBase")
    if any(str(field.get("type")) == "ref" for field in data.get("fields") or []):
        lines.append("from app.db.refs import Ref")
    lines.extend(
        [
            "",
            "",
            f"class {entity}(AuditBase):",
            f"    __tablename__ = \"{table}\"",
            f"    __entity_label__ = \"{label}\"",
        ]
    )
    lines.extend(body or ["    pass"])
    lines.append("")
    return "\n".join(lines)


def _schema(data: dict, header: str) -> str:
    entity = _pascal(data.get("entity") or data.get("name") or data["table"])
    fields = []
    for field in data.get("fields") or []:
        kind = str(field.get("type") or "string")
        py = "str | None"
        if kind == "int" or kind == "ref":
            py = "int | None"
        fields.append(f"    {field['name']}: {py} = None")
    lines = [
        header,
        '"""生成的入参。"""',
        "from __future__ import annotations",
        "",
        "from pydantic import BaseModel",
        "",
        "",
        f"class {entity}Write(BaseModel):",
    ]
    lines.extend(fields or ["    pass"])
    lines.append("")
    return "\n".join(lines)


def _service(data: dict, header: str) -> str:
    slug = _snake(data.get("name") or data.get("entity") or data["table"])
    lines = [
        header,
        '"""生成的服务。业务改动后再生成会写到 service.py.generated。"""',
        "from __future__ import annotations",
        "",
        "",
        f"def page_{slug}():",
        "    return []",
        "",
        "",
        f"def create_{slug}(payload: dict) -> dict:",
        "    return dict(payload)",
        "",
        "",
        f"def update_{slug}(ident: int, payload: dict) -> dict:",
        "    data = dict(payload)",
        "    data[\"id\"] = ident",
        "    return data",
        "",
        "",
        f"def delete_{slug}(ident: int) -> dict:",
        "    return {\"id\": ident}",
        "",
    ]
    return "\n".join(lines)


def _router(data: dict, header: str) -> str:
    slug = _snake(data.get("name") or data.get("entity") or data["table"])
    perm = str(data["perm"]).rstrip(":")
    label = data.get("label") or data.get("entity") or slug
    lines = [
        header,
        '"""生成的路由。"""',
        "from __future__ import annotations",
        "",
        "from fastapi import APIRouter",
        "",
        "from app.api.meta import mark",
        "from app.api.runtime import current_request",
        "",
        "from . import service",
        "",
        "router = APIRouter()",
        "",
        "",
        "def _body() -> dict:",
        "    request = current_request()",
        "    return getattr(request.state, \"json_body\", None) or {}",
        "",
        "",
        f"@mark(perm=\"{perm}:query\", summary=\"查询{label}\")",
        f"def {slug}_page():",
        f"    return service.page_{slug}()",
        "",
        "",
        f"@mark(perm=\"{perm}:create\", summary=\"新建{label}\")",
        f"def {slug}_create():",
        f"    return service.create_{slug}(_body())",
        "",
        "",
        f"@mark(perm=\"{perm}:update\", summary=\"修改{label}\")",
        f"def {slug}_update():",
        "    body = _body()",
        f"    return service.update_{slug}(int(body[\"id\"]), body)",
        "",
        "",
        f"@mark(perm=\"{perm}:delete\", summary=\"删除{label}\")",
        f"def {slug}_delete():",
        "    request = current_request()",
        f"    return service.delete_{slug}(int(request.query_params.get(\"id\")))",
        "",
        "",
        f"router.get(\"/{slug}/page\", summary=\"查询{label}\")({slug}_page)",
        f"router.post(\"/{slug}/create\", summary=\"新建{label}\")({slug}_create)",
        f"router.put(\"/{slug}/update\", summary=\"修改{label}\")({slug}_update)",
        f"router.delete(\"/{slug}/delete\", summary=\"删除{label}\")({slug}_delete)",
        "",
    ]
    return "\n".join(lines)


def _vue(data: dict, header: str) -> str:
    label = data.get("label") or data.get("entity") or data["table"]
    rows = []
    for field in data.get("fields") or []:
        rows.append(f"      <div>{field['name']}</div>")
    body = "\n".join(rows)
    comment = "\n".join(f"<!-- {line[2:]} -->" if line.startswith("# ") else f"<!-- {line} -->" for line in header.splitlines())
    return (
        f"{comment}\n"
        "<template>\n"
        "  <section>\n"
        f"    <h1>{label}</h1>\n"
        f"{body}\n"
        "  </section>\n"
        "</template>\n"
    )


def _test(data: dict, header: str) -> str:
    slug = _snake(data.get("name") or data.get("entity") or data["table"])
    return "\n".join(
        [
            header,
            f"def test_{slug}_scaffold():",
            "    assert True",
            "",
        ]
    )


def generate(definition, out_dir, force: bool = False) -> dict:
    path = Path(definition)
    data, def_hash = _load(path)
    _validate(data)
    header = _headers(def_hash)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "model.py": _model(data, header),
        "schema.py": _schema(data, header),
        "router.py": _router(data, header),
        "index.vue": _vue(data, header),
        "test_generated.py": _test(data, header),
    }
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
    service_text = _service(data, header)
    service_path = out / "service.py"
    if service_path.exists() and not force and body_hash(service_path.read_text(encoding="utf-8")) != body_hash(service_text):
        (out / "service.py.generated").write_text(service_text, encoding="utf-8")
        kept = True
    else:
        service_path.write_text(service_text, encoding="utf-8")
        kept = False
    return {"out": str(out), "service_kept": kept, "def_hash": def_hash}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("definition")
    parser.add_argument("--out", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        generate(args.definition, args.out, force=args.force)
    except ScaffoldError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
