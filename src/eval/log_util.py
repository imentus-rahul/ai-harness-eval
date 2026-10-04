"""stderr logging for live evaluation runs."""

from __future__ import annotations

import sys
from datetime import datetime


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def info(msg: str) -> None:
    print(f"[eval {_ts()}] {msg}", file=sys.stderr, flush=True)


def warn(msg: str) -> None:
    print(f"[eval {_ts()}] WARN {msg}", file=sys.stderr, flush=True)


def error(msg: str) -> None:
    print(f"[eval {_ts()}] ERROR {msg}", file=sys.stderr, flush=True)
