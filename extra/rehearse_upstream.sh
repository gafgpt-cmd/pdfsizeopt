#!/bin/bash
set -euo pipefail
root="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
base=0af13e98d36205168b7699813da3cfddd019946b
sandbox="$(mktemp -d "${TMPDIR:-/tmp}/pdfsizeopt-rehearsal.XXXXXX")"
printf 'Rehearsal workspace: %s\n' "$sandbox"
git clone --shared --no-checkout "$root" "$sandbox/repo"
git -C "$sandbox/repo" fetch https://github.com/T-3B/pdfsizeopt.git master
git -C "$sandbox/repo" worktree add --detach "$sandbox/work" FETCH_HEAD
git -C "$root" diff --binary "$base" HEAD -- . ':!pdfsizeopt.single' > "$sandbox/fork.patch"
git -C "$sandbox/work" apply --3way "$sandbox/fork.patch"
git -C "$sandbox/work" rm --cached --ignore-unmatch pdfsizeopt.single
ln -s "$root/.runtime" "$sandbox/work/.runtime"
ln -s "$root/.venv" "$sandbox/work/.venv"
PATH="$root/.runtime/bin:$PATH" \
  PYTHON3="$root/.venv/bin/python" bash "$sandbox/work/extra/run_fork_tests.sh"
printf 'PASS: replay and tests succeeded; original checkout unchanged.\n'
printf 'Retained disposable workspace for inspection: %s\n' "$sandbox"
