"""python -m app.worker。只启动调度，不挂 HTTP。"""
from __future__ import annotations

from app.worker import registered_jobs


def main() -> None:
    jobs = registered_jobs()
    names = ", ".join(item.name for item in jobs)
    print(f"worker jobs: {names}")


if __name__ == "__main__":
    main()
