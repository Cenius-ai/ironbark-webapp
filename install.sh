#!/usr/bin/env bash
# IronBark setup: installs project-level dependencies, verifies the tool, EXITS.
#
# IronBark itself is standard library only - it runs straight from a checkout
# with `python3 ironbark.py`. This script only adds the declared dev
# dependency (pytest) and the `ironbark` console command on PATH.
# No sudo, no system packages, no services, no network at runtime.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

echo "==> Interpreter"
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 9), "IronBark needs Python 3.9 or newer"'
"$PYTHON" --version

echo "==> Project-level dependencies"
"$PYTHON" -m pip install --upgrade pip setuptools wheel
"$PYTHON" -m pip install -r requirements.txt
"$PYTHON" -m pip install --no-build-isolation -e .

echo "==> Self-check"
"$PYTHON" -c 'import ironbark; print("ironbark", ironbark.VERSION, "imports cleanly")'
"$PYTHON" ironbark.py heat 780 > /dev/null
echo "==> Tests"
"$PYTHON" -m pytest -q

echo
echo "Setup complete. Run: python3 ironbark.py heat 780"
echo "Full walkthrough:   bash demo.sh"
