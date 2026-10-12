"""导出 OpenAPI 与一份稳定的 TypeScript 客户端。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_CLIENT = ROOT.parent / "ims-web" / "src" / "api" / "generated" / "client.ts"


def _sort(value):
    if isinstance(value, dict):
        return {key: _sort(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sort(item) for item in value]
    return value


def _operations(schema: dict) -> list[dict]:
    found = []
    for path in sorted((schema.get("paths") or {})):
        item = schema["paths"][path] or {}
        for method in sorted(item):
            if method.startswith("x-") or method == "parameters":
                continue
            meta = item[method] or {}
            if not isinstance(meta, dict):
                continue
            found.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "summary": str(meta.get("summary") or ""),
                    "operationId": str(meta.get("operationId") or ""),
                }
            )
    return found


def _ts(operations: list[dict]) -> str:
    lines = [
        "/* generated */",
        "export interface ImsOperation {",
        "  method: string;",
        "  path: string;",
        "  summary: string;",
        "  operationId: string;",
        "}",
        "",
        "export const operations: readonly ImsOperation[] = [",
    ]
    for item in operations:
        lines.append(
            "  "
            + json.dumps(item, ensure_ascii=False, separators=(", ", ": "))
            + ","
        )
    lines.extend(
        [
            "];",
            "",
            "export function operationUrl(path: string, params: Record<string, string | number> = {}): string {",
            "  return path.replace(/\\{([^}]+)\\}/g, (_match, key: string) => String(params[key] ?? \"\"));",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def dump_openapi(openapi_path=None, client_path=None, app=None) -> dict:
    if app is None:
        from app.main import create_app

        app = create_app()
    schema = _sort(app.openapi())
    openapi_path = Path(openapi_path) if openapi_path else ROOT / "openapi.json"
    client_path = Path(client_path) if client_path else WEB_CLIENT
    openapi_path.parent.mkdir(parents=True, exist_ok=True)
    client_path.parent.mkdir(parents=True, exist_ok=True)
    openapi_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    client_path.write_text(_ts(_operations(schema)), encoding="utf-8")
    return schema


def main(argv=None) -> int:
    dump_openapi()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
