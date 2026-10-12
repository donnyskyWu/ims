"""仓库静态红线。指向某个根目录，返回问题列表。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

VENDOR_HOST = "dashscope" + ".aliyuncs.com"
VENDOR_MODEL = "qwen3" + ".8-max"
_SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "dist"}
_TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".mjs", ".cjs", ".yml", ".yaml", ".md", ".sql", ".json", ".html"}


def _root(path) -> Path:
    return Path(path)


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def _files(root: Path, suffixes: set[str] | None = None):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if suffixes is not None and path.suffix.lower() not in suffixes:
            continue
        yield path


def _is_router(path: Path) -> bool:
    return path.suffix == ".py" and (path.name == "router.py" or path.name.endswith("_router.py"))


def _is_business(path: Path, root: Path) -> bool:
    rel = _rel(path, root)
    if rel.startswith(("tests/", "tools/", "migrations/", "config/")):
        return False
    if rel.startswith("app/"):
        return rel.startswith(("app/domains/", "app/services/", "app/integrations/"))
    return not (root / "app").is_dir()


def check_handwritten_response(root) -> list[str]:
    root = _root(root)
    pattern = re.compile(r"return\s+\{\s*[\"']code[\"']")
    problems = []
    for path in _files(root, {".py"}):
        if not _is_router(path):
            continue
        if pattern.search(_read(path)):
            problems.append(f"{_rel(path, root)}: 路由手写返回 code")
    return problems


def check_create_all(root) -> list[str]:
    root = _root(root)
    token = "Base.metadata.create_all" + "("
    problems = []
    for path in _files(root, {".py"}):
        if token in _read(path):
            problems.append(f"{_rel(path, root)}: 禁止 Base.metadata.create_all")
    return problems


def check_alter_startup(root) -> list[str]:
    root = _root(root)
    app = root / "app"
    problems = []
    if not app.is_dir():
        return problems
    for path in app.rglob("*.py"):
        if path.name not in {"main.py", "__init__.py"} and "startup" not in path.name:
            continue
        if re.search(r"\bALTER\s+TABLE\b", _read(path), re.I):
            problems.append(f"{_rel(path, root)}: 启动代码出现 ALTER TABLE")
    return problems


def check_live_room_leak(root) -> list[str]:
    root = _root(root)
    token = "live" + "_room"
    problems = []
    for base in (root / "app" / "domains", root / "migrations"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and token in _read(path):
                problems.append(f"{_rel(path, root)}: 业务或迁移出现 live_room")
    return problems


def check_role_branch(root) -> list[str]:
    root = _root(root)
    role_pattern = re.compile("role_key" + r"\s*==\s*[\"']R1[\"']")
    admin_pattern = re.compile("[\"']admin[\"']" + r"\s+in\s+" + "roles")
    problems = []
    for path in _files(root, {".py"}):
        text = _read(path)
        rel = _rel(path, root)
        if role_pattern.search(text):
            problems.append(f"{rel}: 按角色键 R1 分支")
        if admin_pattern.search(text):
            problems.append(f"{rel}: 按 admin 角色名分支")
    return problems


def check_manual_tenant(root) -> list[str]:
    root = _root(root)
    where_token = ".where" + "("
    tenant_token = "tenant_id" + " =="
    problems = []
    for path in _files(root, {".py"}):
        if not _is_business(path, root):
            continue
        text = _read(path)
        if where_token in text and tenant_token in text:
            problems.append(f"{_rel(path, root)}: 业务代码手写租户条件")
    return problems


def check_ops_http(root) -> list[str]:
    root = _root(root)
    ops_path = "/ops" + "/api"
    ops_host = "ops" + "."
    problems = []
    for path in _files(root, {".py"}):
        text = _read(path)
        if "httpx" not in text:
            continue
        if ".get(" not in text and "httpx.get" not in text:
            continue
        if ops_path in text or ops_host in text:
            problems.append(f"{_rel(path, root)}: httpx 访问 ops")
    return problems


def check_vendor_hardcode(root) -> list[str]:
    root = _root(root)
    allowed = "tools/seed/train_ai_default.py"
    problems = []
    for path in _files(root, _TEXT_SUFFIXES):
        rel = _rel(path, root)
        if rel == allowed:
            continue
        text = _read(path)
        if VENDOR_HOST in text:
            problems.append(f"{rel}: 禁止硬编码 {VENDOR_HOST}")
        if VENDOR_MODEL in text:
            problems.append(f"{rel}: 禁止硬编码 {VENDOR_MODEL}")
    return problems


def check_train_ai_isolation(root) -> list[str]:
    root = _root(root)
    base = root / "app" / "integrations" / "train_ai"
    problems = []
    if not base.is_dir():
        return problems
    for path in base.rglob("*.py"):
        text = _read(path)
        if "air_ai" in text:
            problems.append(f"{_rel(path, root)}: 培训 AI 不得引用内容 AI")
    return problems


def check_frontend_paths(root) -> list[str]:
    root = _root(root)
    needle = "/admin-api" + "/ims/"
    problems = []
    for path in _files(root, {".vue", ".ts", ".tsx", ".js", ".jsx"}):
        rel = _rel(path, root)
        if "api/generated" in rel:
            continue
        if needle in _read(path):
            problems.append(f"{rel}: 前端手写管理端路径")
    return problems


def check_seed_apply_call(root) -> list[str]:
    root = _root(root)
    mod = "tools" + ".seed"
    call = "apply" + "("
    problems = []
    for path in _files(root, {".py"}):
        if path.name != "service.py":
            continue
        text = _read(path)
        if mod in text and call in text:
            problems.append(f"{_rel(path, root)}: 业务服务调用种子")
    return problems


def check_route_summary(root) -> list[str]:
    root = _root(root)
    pattern = re.compile(r"router\.(get|post|put|delete|patch|head)\(([^)]*)\)", re.S)
    problems = []
    for path in _files(root, {".py"}):
        if not _is_router(path):
            continue
        for match in pattern.finditer(_read(path)):
            if "summary" not in match.group(2):
                problems.append(f"{_rel(path, root)}: 路由缺少 summary")
                break
    return problems


def scan(root, *, summary: bool = False) -> list[str]:
    problems = []
    problems += check_handwritten_response(root)
    problems += check_create_all(root)
    problems += check_alter_startup(root)
    problems += check_live_room_leak(root)
    problems += check_role_branch(root)
    problems += check_manual_tenant(root)
    problems += check_ops_http(root)
    problems += check_vendor_hardcode(root)
    problems += check_train_ai_isolation(root)
    problems += check_frontend_paths(root)
    problems += check_seed_apply_call(root)
    if summary:
        problems += check_route_summary(root)
    return problems


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = args[0] if args else "."
    include_summary = "--summary" in args
    problems = scan(root, summary=include_summary)
    for item in problems:
        print(item)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
