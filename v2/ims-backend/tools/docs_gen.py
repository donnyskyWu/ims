"""从表引用登记和共享表目录生成三份文档。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "docs"


def _load():
    from app.catalog import SHARED_TABLES
    from app.db.refs import REGISTRY, validate_refs
    from app.domains import all_models

    models = all_models()
    validate_refs(models)
    labels = {model.__tablename__: getattr(model, "__entity_label__", model.__tablename__) for model in models}
    return SHARED_TABLES, dict(REGISTRY), labels, models


def render_tables(shared, labels) -> str:
    lines = ["# 表名登记册", "", "## 共享表", "", "| 表名 | 前缀 | 说明 |", "| --- | --- | --- |"]
    for table, prefix, title in shared:
        lines.append(f"| {table} | {prefix} | {title} |")
    lines.extend(["", f"共享表共 {len(shared)} 张。", "", "## 全部表", "", "| 表名 | 说明 |", "| --- | --- |"])
    for table in sorted(labels):
        lines.append(f"| {table} | {labels[table]} |")
    lines.append("")
    return "\n".join(lines)


def render_refs(registry, labels) -> str:
    lines = ["# 外键字典", "", "| 来源表 | 字段 | 目标表 | 删除策略 | 目标说明 |", "| --- | --- | --- | --- | --- |"]
    for table, column in sorted(registry):
        spec = registry[(table, column)]
        lines.append(
            f"| {table} | {column} | {spec.target} | {spec.on_delete} | {spec.entity_label or labels.get(spec.target, spec.target)} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_er(shared, registry) -> str:
    lines = ["# ER", "", "```mermaid", "erDiagram"]
    for table, prefix, title in shared:
        lines.append(f"  {table} {{")
        lines.append(f"    string prefix \"{prefix}\"")
        lines.append(f"    string title \"{title}\"")
        lines.append("  }")
    for table, column in sorted(registry):
        spec = registry[(table, column)]
        lines.append(f"  {spec.target} ||--o{{ {table} : {column}")
    lines.extend(["```", ""])
    return "\n".join(lines)


def write_docs(out_dir=None) -> list[Path]:
    shared, registry, labels, _models = _load()
    target = Path(out_dir) if out_dir else DEFAULT_DIR
    target.mkdir(parents=True, exist_ok=True)
    files = {
        "表名登记册.md": render_tables(shared, labels),
        "外键字典.md": render_refs(registry, labels),
        "ER.md": render_er(shared, registry),
    }
    written = []
    for name, text in files.items():
        path = target / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def main(argv=None) -> int:
    write_docs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
