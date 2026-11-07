#!/usr/bin/env bash
# Device kernel build recipe. Package entry remains the upstream template.
set -euo pipefail
exec python3 "$(dirname "${BASH_SOURCE[0]}")/build-repro-kernel.py"
