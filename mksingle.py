#!/usr/bin/env python3
"""Build the Python 3 executable archive with the standard library."""

import io
from pathlib import Path
import zipapp

LAUNCHER = b'''#!/bin/sh
P="$(readlink "$0" 2>/dev/null)"
test "$P" && test "${P#/}" = "$P" && P="${0%/*}/$P"
test "$P" || P="$0"
Q="${P%/*}/.venv/bin/python"
test -n "$PDFSIZEOPT_PYTHON" && exec "$PDFSIZEOPT_PYTHON" -- "$0" "$@"
test -x "$Q" && exec "$Q" -- "$0" "$@"
exec python3 -- "$0" "$@"
exit 1
'''


def main():
  root = Path(__file__).resolve().parent
  modules = {'__init__.py', 'binary.py', 'cli.py', 'cff.py', 'float_util.py',
             'image_filters.py', 'main.py', 'psproc.py'}
  for name in modules:
    source = root / 'lib' / 'pdfsizeopt' / name
    compile(source.read_text(encoding='utf-8'), str(source), 'exec')
  target = root / 'pdfsizeopt.single'
  archive = io.BytesIO()
  zipapp.create_archive(
      root / 'lib', target=archive,
      main='pdfsizeopt.cli:run', compressed=True,
      filter=lambda path: (path.as_posix() == 'pdfsizeopt' or
                           path.parent.as_posix() == 'pdfsizeopt' and
                           path.name in modules))
  target.write_bytes(LAUNCHER + archive.getvalue())
  target.chmod(0o755)
  print('Created %s (%d bytes)' % (target, target.stat().st_size))


if __name__ == '__main__':
  main()
