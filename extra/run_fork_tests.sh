#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
root="$PWD"
export PATH="$root/.runtime/bin:$PATH"
export PYTHON3="${PYTHON3:-$root/.venv/bin/python}"
"$PYTHON3" -W error::SyntaxWarning -m py_compile lib/pdfsizeopt/*.py extra/*test.py mksingle.py
"$PYTHON3" pdfsizeopt_test.py
"$PYTHON3" extra/fork_regression_test.py
"$PYTHON3" extra/python3_regression_test.py
"$PYTHON3" extra/preservation_test.py
"$PYTHON3" extra/font_preservation_test.py
"$PYTHON3" "$root/mksingle.py"
PDFSIZEOPT_LAUNCHER="$root/pdfsizeopt.single" "$PYTHON3" extra/preservation_test.py
PDFSIZEOPT_LAUNCHER="$root/pdfsizeopt.single" "$PYTHON3" extra/font_preservation_test.py
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git diff --check; fi
