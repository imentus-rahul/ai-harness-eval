#!/usr/bin/env python3
"""Refresh line/end_line in archify/**/candidate.json from current source files."""

from __future__ import annotations

import json
import re
from pathlib import Path


def function_spans(path: Path) -> list[tuple[int, int, str]]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    spans: list[tuple[int, int, str]] = []
    starts: list[tuple[int, str]] = []
    for i, line in enumerate(lines, start=1):
        m = re.match(r"^def (\w+)\(", line)
        if m:
            starts.append((i, m.group(1)))
    for idx, (start, name) in enumerate(starts):
        end = len(lines)
        if idx + 1 < len(starts):
            end = starts[idx + 1][0] - 1
        spans.append((start, end, name))
    return spans


def span_for_line(spans: list[tuple[int, int, str]], line: int) -> tuple[int, int] | None:
    for start, end, _ in spans:
        if start <= line <= end:
            return start, end
    best = None
    best_dist = 10_000
    for start, end, _ in spans:
        if line < start:
            dist = start - line
        elif line > end:
            dist = line - end
        else:
            return start, end
        if dist < best_dist:
            best_dist = dist
            best = (start, end)
    if best and best_dist <= 40:
        return best
    return None


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    archify = root / "archify"
    updated = 0
    for cand in archify.glob("**/candidate.json"):
        data = json.loads(cand.read_text(encoding="utf-8"))
        nodes = data.get("nodes") or []
        for node in nodes:
            for src in node.get("sources") or []:
                rel = src.get("path")
                if not rel:
                    continue
                path = root / rel
                old_line = src.get("line", 1)
                spans = function_spans(path)
                hit = span_for_line(spans, int(old_line))
                if not hit:
                    continue
                start, end = hit
                if src.get("line") != start or src.get("end_line") != end:
                    src["line"] = start
                    src["end_line"] = end
                    updated += 1
        cand.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"updated {updated} source spans under {archify}")


if __name__ == "__main__":
    main()
