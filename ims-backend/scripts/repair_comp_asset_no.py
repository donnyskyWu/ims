"""一次性修复 ims_comp_asset 重复单号。不在列表接口里调用。

同一租户内重复的 asset_no：保留 id 最小的那条，其余改成同一 CP{YYYYMMDD} 前缀的下一个空号。
必须在 db/compat/20261011_comp_asset_no_unique.sql 加上唯一约束之前执行。

默认 dry-run，只打印映射。确认后再加 --apply。

    python scripts/repair_comp_asset_no.py --dry-run
    python scripts/repair_comp_asset_no.py --apply --output /tmp/comp-asset-no-map.tsv
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import SessionLocal, utcnow
from app.models import CompAsset

BJ = timezone(timedelta(hours=8))
_CP_DAY = re.compile(r"^(CP\d{8})")


@dataclass
class AssetNoRow:
    id: int
    name: str
    asset_no: str


@dataclass
class AssetNoChange:
    id: int
    name: str
    old_no: str
    new_no: str


def plan_repairs(rows: list[AssetNoRow]) -> list[AssetNoChange]:
    """保留每个单号 id 最小的行，其余分配同日前缀的下一个空号。"""
    seen: set[str] = set()
    changes: list[AssetNoChange] = []
    for row in sorted(rows, key=lambda item: item.id):
        current = row.asset_no or ""
        if current and current not in seen:
            seen.add(current)
            continue
        matched = _CP_DAY.match(current)
        prefix = matched.group(1) if matched else f"CP{datetime.now(BJ).strftime('%Y%m%d')}"
        seq = 0
        for no in seen:
            if not no.startswith(prefix):
                continue
            tail = no[len(prefix) :]
            if tail.isdigit():
                seq = max(seq, int(tail))
        seq += 1
        candidate = f"{prefix}{seq:03d}"
        while candidate in seen:
            seq += 1
            candidate = f"{prefix}{seq:03d}"
        changes.append(AssetNoChange(id=row.id, name=row.name, old_no=current, new_no=candidate))
        seen.add(candidate)
    return changes


def format_log(changes: list[AssetNoChange], *, mode: str, scanned: int) -> str:
    lines = [
        f"mode={mode}",
        f"scanned={scanned}",
        f"changes={len(changes)}",
        "asset_id\tname\told_no\tnew_no",
    ]
    if not changes:
        lines.append("no changes")
    else:
        for change in changes:
            lines.append(f"{change.id}\t{change.name}\t{change.old_no}\t{change.new_no}")
    return "\n".join(lines) + "\n"


def load_rows(db: Session) -> list[AssetNoRow]:
    rows = db.scalars(select(CompAsset).order_by(CompAsset.id.asc())).all()
    return [AssetNoRow(id=int(row.id), name=row.comp_name_std or "", asset_no=row.asset_no or "") for row in rows]


def apply_changes(db: Session, changes: list[AssetNoChange]) -> None:
    for change in changes:
        row = db.get(CompAsset, change.id)
        if row is None:
            continue
        row.asset_no = change.new_no
        row.updated_at = utcnow()
    db.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="修复重复的竞品库单号（默认只打印，不写库）")
    parser.add_argument("--apply", action="store_true", help="写回数据库。省略时为 dry-run")
    parser.add_argument("--dry-run", action="store_true", help="只打印 old→new 映射")
    parser.add_argument("--output", default="", help="把同样的映射日志写入文件")
    args = parser.parse_args(argv)
    mode = "apply" if args.apply else "dry-run"
    db = SessionLocal()
    try:
        rows = load_rows(db)
        changes = plan_repairs(rows)
        text = format_log(changes, mode=mode, scanned=len(rows))
        sys.stdout.write(text)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(text)
        if args.apply and changes:
            apply_changes(db, changes)
            db.commit()
        else:
            db.rollback()
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
