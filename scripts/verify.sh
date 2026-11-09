#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
python3 -m compileall -q boot_order_atlas scripts tests
python3 scripts/check.py
