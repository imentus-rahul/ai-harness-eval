"""Applied after the agent finishes — same checks as visible tests."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parent.parent / "repo"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
