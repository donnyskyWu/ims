"""扫描业务源码，禁止 OPS HTTP 与芋道依赖。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
BANNED = ("https://ops.", "ops.base-url", "FeignClient", "yudao", "@DS(")


def main() -> int:
    bad = []
    for path in ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in BANNED:
            if token in text:
                bad.append(f"{path}: {token}")
    if bad:
        print("\n".join(bad))
        return 1
    print("forbid_ops_http ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
