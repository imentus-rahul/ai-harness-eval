#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cp tasks/registry.bootstrap.yaml tasks/registry.yaml
pytest -q
python3 -m eval --dry-run
python3 presentation/src/build_deck.py
test -f output/good-harness-example/summary.json
test -f output/bad-harness-example/summary.json
test -f presentation/output/harness-eval.pptx
echo "e2e validation OK"
