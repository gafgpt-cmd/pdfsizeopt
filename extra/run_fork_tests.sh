#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
root="$PWD"
export PATH="$root/.runtime/bin:$PATH"
export PYTHON2="${PYTHON2:-$root/.runtime/python2/bin/python2.7}"
python3_test="${PYTHON3:-$root/.venv/bin/python}"
"$PYTHON2" -m py_compile lib/pdfsizeopt/main.py extra/fork_regression_test.py
"$PYTHON2" pdfsizeopt_test.py
"$PYTHON2" extra/fork_regression_test.py
"$python3_test" -m py_compile extra/preservation_test.py
"$python3_test" extra/preservation_test.py
"$PYTHON2" "$root/mksingle.py"
PDFSIZEOPT_LAUNCHER="$root/pdfsizeopt.single" "$python3_test" extra/preservation_test.py
git diff --check
