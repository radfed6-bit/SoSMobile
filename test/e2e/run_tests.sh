#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== Launching SoSMobile E2E Test Suite ==="
python3 "${SCRIPT_DIR}/test_runner.py" "$@"
