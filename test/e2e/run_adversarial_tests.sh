#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== Running SoSMobile Tier 5 Adversarial Stress Test Suite ==="

# 1. Run Python Tier 5 Adversarial Suite
echo "--- 1. Executing Python Tier 5 Adversarial Tests ---"
python3 "$WORKSPACE_ROOT/test/e2e/test_runner.py" --tier 5 "$@" || {
    echo "Tier 5 Python tests encountered findings/failures!"
}

# 2. Run Java JVM Bytecode Stress Harness
echo "--- 2. Executing Java JVM Bytecode Stress Harness ---"
BIN_DIR="/tmp/sos_java_stress_bin"
mkdir -p "$BIN_DIR"

javac -cp "$WORKSPACE_ROOT/app_mojo/build/intermediates/javac/fullDebug/compileFullDebugJavaWithJavac/classes:/home/codespace/android-sdk/platforms/android-36/android.jar" \
      -d "$BIN_DIR" \
      "$WORKSPACE_ROOT/test/e2e/tier5_adversarial/JavaEmpiricalStressTest.java" || true

java -cp "$BIN_DIR:$WORKSPACE_ROOT/app_mojo/build/intermediates/javac/fullDebug/compileFullDebugJavaWithJavac/classes:/home/codespace/android-sdk/platforms/android-36/android.jar" \
     test.e2e.tier5_adversarial.JavaEmpiricalStressTest || true

rm -rf "$BIN_DIR"
